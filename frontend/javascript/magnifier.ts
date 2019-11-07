/*

Original by Copyright (c) Andrey Polischuk <me@andrepolischuk.com> (https://andrepolischuk.com)
Licensed under The MIT License (MIT)
Ported to TypeScript and simplified + zoom
*/

function insertAfter(node: HTMLElement, ref: HTMLElement) {
  return ref.parentNode && ref.parentNode.insertBefore(node, ref.nextSibling);
}

function globalOffset(el: HTMLElement) {
  const { top, left } = el.getBoundingClientRect();
  const { pageYOffset, pageXOffset } = window;

  return {
    left: left + pageXOffset,
    top: top + pageYOffset,
  };
}

function isPointerInside(el: HTMLElement, event: Touch | MouseEvent) {
  const { pageX, pageY } = event;
  const { left, top } = globalOffset(el);
  const { offsetWidth, offsetHeight } = el;

  return pageX >= left && pageX <= left + offsetWidth &&
    pageY >= top && pageY <= top + offsetHeight;
}

export default class Magnifier {
  public el: HTMLImageElement;
  public lens: HTMLDivElement;
  public imageWidth: number = 0;
  public imageHeight: number = 0;
  public originalSrc: string;
  public verticalOffset = 60;
  public width = 200;
  public height = 150;
  public zoom = 1.5;
  public minZoom = 1.5;
  public maxZoom = 3;
  public zoomStep = 0.5;

  constructor(el: HTMLImageElement) {
    this.el = el;
    this.el.style.cursor = "zoom-in";
    const {offsetWidth} = this.el;
    this.width = Math.max(this.width, offsetWidth * 0.6);
    this.originalSrc = el.dataset.zoom || "";
    this.lens = document.createElement("div");
    this.lens.className = "magnifier";
    this.lens.style.width = this.width + "px";
    this.lens.style.height = this.height + "px";
    this.handleLoad = this.handleLoad.bind(this);
    this.handleTouchMove = this.handleTouchMove.bind(this);
    this.handleTouchEnd = this.handleTouchEnd.bind(this);
    this.handleZoom = this.handleZoom.bind(this);
    insertAfter(this.lens, this.el);
    this.show();
    this.calcImageSize();
    this.bind();
  }

  public calcImageSize() {
    const orig = document.createElement("img");
    orig.style.position = "absolute";
    orig.style.width = "auto";
    orig.style.visibility = "hidden";
    orig.src = this.originalSrc;
    orig.onload = () => {
      this.imageWidth = orig.naturalWidth;
      this.imageHeight = orig.naturalHeight;
      this.handleLoad();
    };
  }

  public bind() {
    this.el.addEventListener("click", this.handleZoom, false);
    this.el.addEventListener("mousemove", this.handleTouchMove, false);
    this.el.addEventListener("mouseleave", this.handleTouchEnd, false);
    this.el.addEventListener("touchstart", this.handleTouchMove, false);
    this.el.addEventListener("touchmove", this.handleTouchMove, false);
    this.el.addEventListener("touchend", this.handleTouchEnd, false);
    this.lens.addEventListener("mousemove", this.handleTouchMove, false);
    this.lens.addEventListener("mouseleave", this.handleTouchEnd, false);
    this.lens.addEventListener("touchmove", this.handleTouchMove, false);
    this.lens.addEventListener("touchend", this.handleTouchEnd, false);
    return this;
  }

  public unbind() {
    this.el.removeEventListener("click", this.handleZoom, false);
    this.el.removeEventListener("mousemove", this.handleTouchMove, false);
    this.el.removeEventListener("mouseleave", this.handleTouchEnd, false);
    this.el.removeEventListener("touchstart", this.handleTouchMove, false);
    this.el.removeEventListener("touchmove", this.handleTouchMove, false);
    this.el.removeEventListener("touchend", this.handleTouchEnd, false);
    this.lens.removeEventListener("mousemove", this.handleTouchMove, false);
    this.lens.removeEventListener("mouseleave", this.handleTouchEnd, false);
    this.lens.removeEventListener("touchmove", this.handleTouchMove, false);
    this.lens.removeEventListener("touchend", this.handleTouchEnd, false);
    return this;
  }

  public handleLoad() {
    this.hide();
    this.lens.style.visibility = "visible";
    this.lens.style.backgroundImage = `url(${this.originalSrc})`;
    this.setZoom(null);
  }

  public handleTouchMove(event: TouchEvent | MouseEvent) {
    event.preventDefault();
    if (event instanceof window.MouseEvent) {
      this.handleMove(event);
    } else if (window.TouchEvent && event instanceof window.TouchEvent) {
      this.handleMove(event.changedTouches[0]);
    }
  }

  public handleMove(touch: Touch | MouseEvent) {
    if (isPointerInside(this.el, touch)) {
      this.show();
      const { pageX, pageY } = touch;
      const { left, top } = globalOffset(this.el);
      const { offsetLeft, offsetTop } = this.el;
      const borderWidth = 2;
      const imageX = ((left - pageX) * this.zoom) + ((this.width / 2) - borderWidth);
      const imageY = ((top - pageY) * this.zoom) + ((this.height / 2) - borderWidth);
      let x = pageX - (this.width / 2) - (left !== offsetLeft ? left - offsetLeft : 0);
      const y = pageY - (this.height / 2) - (top !== offsetTop ? top - offsetTop : 0) - this.verticalOffset;
      x = Math.min(document.body.clientWidth - this.width, Math.max(x, 0));
      this.lens.style.left = `${x}px`;
      this.lens.style.top = `${y}px`;
      this.lens.style.backgroundPosition = `${imageX}px ${imageY}px`;
    } else {
      this.hide();
    }
  }

  public handleTouchEnd() {
    this.hide();
  }

  public handleZoom(e: MouseEvent) {
    let zoom = this.zoom;
    zoom += this.zoomStep;
    if (zoom > this.maxZoom) {
      zoom = this.minZoom;
    }
    if (zoom + this.zoomStep > this.maxZoom) {
      this.el.style.cursor = "zoom-out";
      this.lens.style.cursor = "zoom-out";
    } else {
      this.el.style.cursor = "zoom-in";
      this.lens.style.cursor = "zoom-in";
    }
    this.setZoom(zoom);
    this.handleMove(e);
  }

  public setZoom(zoom: number | null) {
    const { offsetWidth, offsetHeight } = this.el;
    if (zoom === null) {
      const ratio = offsetWidth / this.imageWidth;
      if (ratio < 0.1) {
        zoom = 3;
      } else if (ratio < 0.2) {
        zoom = 2.5;
      } else if (ratio < 0.3) {
        zoom = 2;
      } else {
        zoom = 1.5;
      }
    }
    this.zoom = zoom;

    const w = offsetWidth * this.zoom;
    const h = offsetHeight * this.zoom;
    this.lens.style.backgroundSize = `${w}px ${h}px`;
  }

  public show() {
    this.lens.style.display = "block";
    return this;
  }

  public hide() {
    this.lens.style.display = "none";
    return this;
  }

  public destroy() {
    this.unbind();
    this.lens.remove();
  }
}

const makeMagnifier = (zoomImage: HTMLImageElement) => {
  const zoomWidth = zoomImage.dataset.zoomwidth;
  if (zoomWidth) {
    if (zoomImage.offsetWidth / parseInt(zoomWidth, 10) > 0.5) {
      // Don't offer zoom when image is sufficiently large
      return;
    }
  }
  return new Magnifier(zoomImage);
};

const zoomImages = document.querySelectorAll("img[data-zoom]");
(Array.from(zoomImages) as HTMLImageElement[]).forEach((zoomImage) => {
  if (zoomImage.offsetWidth === 0) {
    /* Wait for image load */
    zoomImage.addEventListener("load", () => {
      makeMagnifier(zoomImage);
    });
  } else {
    return new Magnifier(zoomImage);
  }
});
