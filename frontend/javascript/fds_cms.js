import Room from "froide/frontend/javascript/lib/websocket.ts"

let room
let userlistContainer

const WS_URL = '/ws/fds-cms/edit-plugin/'
const PLUGIN_ID_PATTERN = /edit-plugin\/(\d+)\//

const renderList = (userList) => {
  if (!userlistContainer) {
    let foot = document.querySelector('.cms-modal-foot')
    userlistContainer = document.createElement('div')
    userlistContainer.classList.add('fds-cms-users')
    userlistContainer.style.color = 'red'
    userlistContainer.style.padding = '1rem'
    foot.prepend(userlistContainer)
  }
  userlistContainer.innerText = userList.join(', ')
}

const setupRoom = () => {
  let iframe = document.querySelector('.cms-modal-frame iframe')
  let match = PLUGIN_ID_PATTERN.exec(iframe.src)
  if (match === null) {
    return
  }
  let pluginId = match[1]
  
  room = new Room(`${WS_URL}${pluginId}/`)

  room.connect().on('userlist', (data) => {
    renderList(data.userlist)
  })
}

CMS.$(window).on('cms-modal-load', function () {
  window.setTimeout(setupRoom, 1000)
}); 

CMS.$(window).on('cms-modal-close', function () {
  renderList([])
  if (room) {
    room.close()
    room = null
  }
});
