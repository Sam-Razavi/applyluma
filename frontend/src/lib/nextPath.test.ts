import { describe, it, expect, beforeEach } from 'vitest'
import { consumeNextPath, getSafeNextPath, rememberNextPath } from './nextPath'

describe('nextPath', () => {
  beforeEach(() => sessionStorage.clear())

  it('only allows same-site paths', () => {
    expect(getSafeNextPath('/extension-auth')).toBe('/extension-auth')
    expect(getSafeNextPath('https://evil.example')).toBe('/dashboard')
    expect(getSafeNextPath('//evil.example')).toBe('/dashboard')
    expect(getSafeNextPath('/login')).toBe('/dashboard')
    expect(getSafeNextPath(null)).toBe('/dashboard')
  })

  it('survives a trip through OAuth and is used once', () => {
    rememberNextPath('/extension-auth')
    expect(consumeNextPath()).toBe('/extension-auth')
    expect(consumeNextPath()).toBe('/dashboard')
  })

  it('never remembers an unsafe destination', () => {
    rememberNextPath('//evil.example')
    expect(consumeNextPath()).toBe('/dashboard')
  })
})
