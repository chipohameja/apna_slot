// frappe-ui composes a failed call's message as `${type}: ${message}`; the exception
// class name is noise to the person reading the form.
export function humanMessage(error) {
  if (!error) return null
  return error.type ? error.message.replace(`${error.type}: `, '') : error.message
}
