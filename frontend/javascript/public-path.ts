const staticUrl = document.body?.dataset?.staticurl
const prefix = staticUrl || '/static/'
__webpack_public_path__ = prefix + 'js/'
