import { reactive } from 'vue'
import { call, useCall } from 'frappe-ui'

const GUEST = { user: 'Guest', full_name: 'Guest', is_guest: true, roles: [], publishers: [] }

export const session = reactive({ ...GUEST, isReady: false })

const sessionCall = useCall({
  url: '/api/v2/method/apna_slot.api.auth.get_session_user',
  immediate: false,
})

export async function loadSession() {
  const data = await sessionCall.execute()
  Object.assign(session, data ?? GUEST, { isReady: true })
  return session
}

export async function logIn(email, password) {
  await call('login', { usr: email, pwd: password })
}

export async function logOut() {
  await call('logout')
  landOn('/login')
}

export function landOn(path) {
  // a new session carries a new CSRF token, so leave the SPA rather than route
  window.location.href = `/apnaslot${path}`
}
