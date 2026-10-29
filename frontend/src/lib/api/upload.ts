import { ApiError, parseApiError } from "./errors"

const API_PREFIX = "/api"

// fetch não informa progresso de envio; XHR sim (`meetings` 35). Cookie vai por mesma origem.
export function postForm<T>(
  path: string,
  form: FormData,
  onProgress: (fraction: number) => void = () => {}
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open("POST", `${API_PREFIX}${path}`)
    xhr.setRequestHeader("Accept", "application/json")
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && e.total > 0) onProgress(e.loaded / e.total)
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as T)
        return
      }
      const response = new Response(xhr.responseText || null, {
        status: xhr.status,
      })
      parseApiError(response).then(reject, reject)
    }
    xhr.onerror = () =>
      reject(new ApiError(0, "network_error", "Sem conexão com o servidor."))
    xhr.send(form)
  })
}
