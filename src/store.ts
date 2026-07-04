import { reactive } from 'vue'

export const store = reactive({
  page: 'home' as 'home' | 'proposals' | 'detail' | 'profile',
  selectedId: '' as string,
  wallet: null as string | null,
  theme: (localStorage.getItem('agora-theme') || 'dark') as 'dark' | 'light'
})

export function navigate(page: typeof store.page, id?: string) {
  store.page = page
  if (id !== undefined) store.selectedId = String(id)
  window.scrollTo({ top: 0 })
}

export function setTheme(t: 'dark' | 'light') {
  store.theme = t
  localStorage.setItem('agora-theme', t)
  document.documentElement.setAttribute('data-theme', t)
}