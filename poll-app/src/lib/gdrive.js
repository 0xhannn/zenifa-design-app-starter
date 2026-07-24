/** Extract Google Drive file id from common share URL shapes. */
export function extractDriveId(url) {
  if (!url || typeof url !== 'string') return null
  const s = url.trim()
  if (!s) return null

  // /file/d/FILE_ID/
  let m = s.match(/\/file\/d\/([a-zA-Z0-9_-]{10,})/)
  if (m) return m[1]

  // open?id=FILE_ID or uc?id=FILE_ID
  m = s.match(/[?&]id=([a-zA-Z0-9_-]{10,})/)
  if (m) return m[1]

  // drive.google.com/uc?export=view&id=
  m = s.match(/drive\.google\.com\/(?:uc|thumbnail)[^#]*[?&]id=([a-zA-Z0-9_-]{10,})/)
  if (m) return m[1]

  // bare id pasted
  if (/^[a-zA-Z0-9_-]{25,}$/.test(s)) return s

  // last-resort long token (same heuristic as main.py)
  m = s.match(/[-\w]{25,}/)
  return m ? m[0] : null
}

export function gdriveThumbnail(url, size = 800) {
  const id = extractDriveId(url)
  if (!id) return ''
  return `https://drive.google.com/thumbnail?sz=w${size}&id=${id}`
}

export function gdriveViewUrl(url) {
  const id = extractDriveId(url)
  if (!id) return url
  return `https://drive.google.com/file/d/${id}/view`
}

export function guessNameFromUrl(url, index = 0) {
  const id = extractDriveId(url)
  if (!id) return `Desain ${index + 1}`
  return `Desain ${index + 1}`
}

/** Parse multi-line paste; keep unique valid-looking links. */
export function parseLinkLines(text) {
  const lines = String(text || '')
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)

  const seen = new Set()
  const out = []
  for (const line of lines) {
    const id = extractDriveId(line)
    const key = id || line
    if (seen.has(key)) continue
    seen.add(key)
    out.push(line)
  }
  return out
}