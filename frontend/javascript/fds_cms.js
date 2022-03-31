/* globals CMS */

import Room from 'froide/frontend/javascript/lib/websocket.ts'

let room
let modalOpen = false
let userlistContainer

const WS_URL = '/ws/fds-cms/edit-plugin/'
const PLUGIN_ID_PATTERN = /edit-plugin\/(\d+)\//

const renderList = (userList) => {
  if (!userlistContainer) {
    const foot = document.querySelector('.cms-modal-foot')
    userlistContainer = document.createElement('div')
    userlistContainer.classList.add('fds-cms-users')
    userlistContainer.style.color = 'red'
    userlistContainer.style.padding = '1rem'
    foot.prepend(userlistContainer)
  }
  userlistContainer.innerText = userList.join(', ')
}

const setupRoom = () => {
  if (!modalOpen) {
    return
  }
  const iframe = document.querySelector('.cms-modal-frame iframe')
  if (iframe === null) {
    if (modalOpen) {
      window.setTimeout(setupRoom, 1000)
    }
    return
  }
  const match = PLUGIN_ID_PATTERN.exec(iframe.src)
  if (match === null) {
    return
  }
  const pluginId = match[1]

  room = new Room(`${WS_URL}${pluginId}/`)

  room.connect().on('userlist', (data) => {
    renderList(data.userlist)
  })
}

CMS.$(window).on('cms-modal-load', function () {
  modalOpen = true
  window.setTimeout(setupRoom, 1000)
})

CMS.$(window).on('cms-modal-close', function () {
  modalOpen = false
  renderList([])
  if (room) {
    room.send({ type: 'left' })
    room.close()
    room = null
  }
})
