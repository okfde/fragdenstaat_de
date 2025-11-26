import '../styles/ubf.scss'
import './donation-form'

import { Tooltip } from 'bootstrap'
import arrowLeft from '../img/ubf/arrow-left.svg?raw'
import arrowRight from '../img/ubf/arrow-right.svg?raw'
import './misc/reference'
import './misc/matomo'

// map element
const svg = document.querySelector<SVGElement>('#map-container svg')
const infoContainer = document.querySelector('#map-info-container')

interface Organization {
  name: string
  url: string
  location: string
  x: number
  y: number
  description: string
  tags: string[]
}

class MapOrganization extends HTMLElement {
  container = document.createElement('article')
  headline = document.createElement('h3')
  location = document.createElement('span')
  url = document.createElement('a')
  description = document.createElement('p')
  tagList = document.createElement('ul')
  navigation = document.createElement('nav')

  constructor(public item: Organization) {
    super()
    this.container.classList.add('text-bg-white', 'rounded-4', 'p-2', 'p-md-3')
    this.tagList.classList.add(
      'list-unstyled',
      'd-flex',
      'flex-wrap',
      'gap-1',
      'mt-2'
    )
    this.url.classList.add('link-underline-merlot-25', 'link-offset-2')
    this.url.target = '_blank'

    this.navigation.classList.add(
      'hstack',
      'gap-2',
      'justify-content-end',
      'mb-2'
    )

    const previous = document.createElement('button')
    const next = document.createElement('button')

    previous.classList.add('btn', 'btn-outline-secondary')
    next.classList.add('btn', 'btn-outline-secondary')
    previous.innerHTML = arrowLeft
    next.innerHTML = arrowRight
    previous.ariaLabel = 'Zurück'
    next.ariaLabel = 'Vorwärts'

    previous.addEventListener('click', () => {
      this.dispatchEvent(new CustomEvent('previous'))
    })

    next.addEventListener('click', () => {
      this.dispatchEvent(new CustomEvent('next'))
    })

    this.navigation.appendChild(previous)
    this.navigation.appendChild(next)

    this.container.appendChild(this.headline)

    const byline = document.createElement('div')
    byline.classList.add('d-flex', 'flex-wrap', 'mb-2', 'small')

    const divider = document.createElement('span')
    divider.innerText = '⋅'
    divider.ariaHidden = 'true'
    divider.classList.add('mx-1')

    byline.appendChild(this.location)
    byline.append(divider)
    byline.append(this.url)

    this.container.appendChild(byline)
    this.container.appendChild(this.description)
    this.container.appendChild(this.tagList)

    this.update()
  }

  update(item?: Organization) {
    if (item) this.item = item

    this.headline.innerText = this.item.name
    this.location.innerText = this.item.location
    this.description.innerText = this.item.description

    const url = new URL(this.item.url)
    this.url.innerText = url.hostname
    this.url.href = this.item.url

    const tags = this.item.tags.map((tag) => {
      const el = document.createElement('li')
      el.classList.add(
        'badge',
        'bg-merlot-100',
        'text-merlot-100',
        'bg-opacity-10'
      )
      el.innerText = tag
      return el
    })

    this.tagList.innerHTML = ''
    tags.forEach((t) => this.tagList.appendChild(t))
  }

  connectedCallback() {
    this.appendChild(this.navigation)
    this.appendChild(this.container)
  }
}
customElements.define('map-organization', MapOrganization)

if (svg) {
  let currentIndex = 0
  const organizations: Organization[] = await (
    await fetch(
      'https://media.frag-den-staat.de/files/media/main/43/24/432480e1-1eb3-45b4-ae9a-a4fc34d8b0ad/orgas.json'
    )
  ).json()

  const infoBox = new MapOrganization(organizations[currentIndex])
  infoBox.addEventListener('previous', () => {
    if (currentIndex == 0) currentIndex = organizations.length - 1
    else currentIndex -= 1
    infoBox.update(organizations[currentIndex])
  })
  infoBox.addEventListener('next', () => {
    currentIndex += 1
    currentIndex %= organizations.length
    infoBox.update(organizations[currentIndex])
  })
  infoContainer?.appendChild(infoBox)

  const groups: SVGGElement[] = []

  organizations
    .filter((i) => i.x && i.y)
    .forEach((i) => {
      const g = document.createElementNS('http://www.w3.org/2000/svg', 'g')
      g.innerHTML = `<line x1="10.5" y1="10" x2="10.5" y2="33" stroke="white"/><circle cx="10.5" cy="10.5" r="10.5" fill="#FF6C03" stroke="#006f59" stroke-width="0.5" />`
      const transform = `translate(${i.x - 11} ${i.y - 24})` // offset for circle/line
      g.setAttribute('transform', transform)
      g.setAttribute('class', 'map-pin')
      g.addEventListener('click', () => infoBox.update(i))

      const shadow = document.createElementNS('http://www.w3.org/2000/svg', 'g')
      shadow.innerHTML =
        '<line opacity="0.5" x1="21.3536" y1="21.3536" x2="10.3536" y2="32.3536" stroke="url(#gradient)"/>'
      shadow.setAttribute('transform', transform)

      svg.appendChild(shadow)
      groups.push(g)
      new Tooltip(g, {
        placement: 'top',
        offset: [0, 10],
        title: i.name
      })
    })

  groups.forEach((g) => svg.appendChild(g))
}
