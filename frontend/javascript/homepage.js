import { Modal} from "bootstrap.native/dist/bootstrap-native-v4";
import Glide from '@glidejs/glide'

// Video introduction
const modalTrigger = document.getElementById('videoModalTrigger')
const modalContainer = document.getElementById('videoModalContainer')

if (modalTrigger && modalContainer) {
  const modalContent = '<div class="modal-body"><div style="padding:56.25% 0 0 0;position:relative;"><iframe src="https://player.vimeo.com/video/102604678?autoplay=1&title=0&byline=0&portrait=0" style="position:absolute;top:0;left:0;width:100%;height:100%;" frameborder="0" allow="autoplay; fullscreen" allowfullscreen></iframe></div><script src="https://player.vimeo.com/api/player.js"></script></div>'
  const videoModalInstance = new Modal(modalContainer)
  modalTrigger.addEventListener('click', function(){
    videoModalInstance.setContent(modalContent);
    videoModalInstance.show();
  }, false);
  modalContainer.addEventListener('hidden.bs.modal', function(){
    // remove content so player stop playing
    videoModalInstance.setContent('');
  }, false);

}

// glide slider
// ref: https://glidejs.com/docs/options/
new Glide('.campaign-slider__wrap', {
  // startAt: 0,
  perView: 3,
  gap: 30,
  peek: 80,

  // apply bootstrap breakepoints
  // "Collection of options applied at specified media breakpoints.
  // For example, display two slides per view under 800px"
  breakpoints: {
    576: {
      perView: 1,
      peek: 0,
    },
    768: {
      perView: 1,
      peek: 0,
    },
    992: {
      perView: 2,
      peek: { before: 0, after: 0 },
    },
    1200: {
      perView: 2,
      gap: 0,
      peek: { before: 50, after: 250 },
    }
  }
}).mount()