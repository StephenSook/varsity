// Verbalize numbers + units for the screen-reader spoken form. A blind fan hears the aria-live
// text, and screen readers read "5.69 m" inconsistently across AT and languages (the unit "m" is
// often spoken as the letter "m"; decimals vary). So for the SPOKEN form we render "5.69 m" as
// "five point six nine metres" - unambiguous, in the chosen language. This is the relevant subset
// of ClearSpeak / MathSpeak (Soiffer; Speech Rule Engine) for our domain: an ordinary decimal
// spoken digit-by-digit after the point, with the unit spoken in full. No dependency (our number
// range is small), which also keeps the dependency tree fully permissive. The VISIBLE text keeps
// the compact digits (dual-track); only the spoken aria-live text is verbalized.

type Lng = 'en' | 'es' | 'fr' | 'pt' | 'de'

// 0..19 (Spanish carries 20..29 inline because they are written as one word).
const ONES: Record<Lng, string[]> = {
  en: ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen'],
  es: ['cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'dieciséis', 'diecisiete', 'dieciocho', 'diecinueve', 'veinte', 'veintiuno', 'veintidós', 'veintitrés', 'veinticuatro', 'veinticinco', 'veintiséis', 'veintisiete', 'veintiocho', 'veintinueve'],
  fr: ['zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf'],
  pt: ['zero', 'um', 'dois', 'três', 'quatro', 'cinco', 'seis', 'sete', 'oito', 'nove', 'dez', 'onze', 'doze', 'treze', 'catorze', 'quinze', 'dezesseis', 'dezessete', 'dezoito', 'dezenove'],
  de: ['null', 'eins', 'zwei', 'drei', 'vier', 'fünf', 'sechs', 'sieben', 'acht', 'neun', 'zehn', 'elf', 'zwölf', 'dreizehn', 'vierzehn', 'fünfzehn', 'sechzehn', 'siebzehn', 'achtzehn', 'neunzehn'],
}
// tens digit 2..9
const TENS: Record<Lng, string[]> = {
  en: ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'],
  es: ['', '', 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa'],
  fr: ['', '', 'vingt', 'trente', 'quarante', 'cinquante', 'soixante', '', 'quatre-vingt', ''],
  pt: ['', '', 'vinte', 'trinta', 'quarenta', 'cinquenta', 'sessenta', 'setenta', 'oitenta', 'noventa'],
  de: ['', '', 'zwanzig', 'dreißig', 'vierzig', 'fünfzig', 'sechzig', 'siebzig', 'achtzig', 'neunzig'],
}
const POINT: Record<Lng, string> = { en: 'point', es: 'coma', fr: 'virgule', pt: 'vírgula', de: 'Komma' }
const UNIT: Record<Lng, { m: string; cm: string }> = {
  en: { m: 'metres', cm: 'centimetres' },
  es: { m: 'metros', cm: 'centímetros' },
  fr: { m: 'mètres', cm: 'centimètres' },
  pt: { m: 'metros', cm: 'centímetros' },
  de: { m: 'Meter', cm: 'Zentimeter' },
}

function tensOnes(t: number, o: number, lang: Lng): string {
  const tens = TENS[lang]
  const ones = ONES[lang]
  if (lang === 'de') return o === 0 ? tens[t] : `${o === 1 ? 'ein' : ones[o]}und${tens[t]}`
  if (lang === 'es') return o === 0 ? tens[t] : `${tens[t]} y ${ones[o]}`
  if (lang === 'pt') return o === 0 ? tens[t] : `${tens[t]} e ${ones[o]}`
  if (lang === 'fr') {
    if (t === 7) return o === 0 ? 'soixante-dix' : o === 1 ? 'soixante et onze' : `soixante-${ones[10 + o]}`
    if (t === 9) return `quatre-vingt-${ones[10 + o]}`
    if (t === 8) return o === 0 ? 'quatre-vingts' : `quatre-vingt-${ones[o]}`
    return o === 0 ? tens[t] : o === 1 ? `${tens[t]} et un` : `${tens[t]}-${ones[o]}`
  }
  return o === 0 ? tens[t] : `${tens[t]}-${ones[o]}`
}

function wordsForInt(n: number, lang: Lng): string {
  const ones = ONES[lang]
  if (n < ones.length) return ones[n]
  if (n < 100) return tensOnes(Math.floor(n / 10), n % 10, lang)
  // Out of our margin/cm range; speak digit-by-digit as a safe fallback.
  return String(n).split('').map((d) => ONES[lang][Number(d)]).join(' ')
}

function verbalizeNumber(numStr: string, lang: Lng): string {
  const [intPart, fracPart] = numStr.replace(',', '.').split('.')
  let words = wordsForInt(parseInt(intPart, 10) || 0, lang)
  if (fracPart) {
    const digits = fracPart.split('').map((d) => ONES[lang][Number(d)]).join(' ')
    words += ` ${POINT[lang]} ${digits}`
  }
  return words
}

// A number, then a length unit (abbreviation or full word, any of the five languages).
const UNIT_RE = /(\d+(?:[.,]\d+)?)\s*(centímetros?|centimetros?|centimètres?|centimetres?|centimeters?|zentimetern?|metros?|mètres?|metres?|meters?|meter|cm|m)\b/gi

const LANGS: Lng[] = ['es', 'fr', 'pt', 'de']

/** Render every "<number> <unit>" in the text as spoken words for the screen reader. Leaves bare
 *  numbers (e.g. a Law number) untouched. Idempotent: re-running on verbalized text is a no-op. */
export function verbalizeForSpeech(text: string, bcp47: string): string {
  const lang = (LANGS.find((l) => bcp47.toLowerCase().startsWith(l)) ?? 'en') as Lng
  return text.replace(UNIT_RE, (_m, num: string, unit: string) => {
    const cat = /cm|centi|zenti|centí/i.test(unit) ? 'cm' : 'm'
    return `${verbalizeNumber(num, lang)} ${UNIT[lang][cat]}`
  })
}
