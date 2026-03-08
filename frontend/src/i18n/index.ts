import { createI18n } from 'vue-i18n'
import en from './en.json'
import nl from './nl.json'

const savedLocale = localStorage.getItem('locale') ?? 'nl'

export const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: 'en',
  messages: { en, nl },
})
