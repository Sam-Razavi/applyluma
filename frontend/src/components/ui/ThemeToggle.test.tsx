import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import ThemeToggle from './ThemeToggle'
import { useThemeStore } from '../../stores/theme'

describe('ThemeToggle', () => {
  beforeEach(() => {
    useThemeStore.setState({ dark: false })
    document.documentElement.classList.remove('dark')
  })

  it('starts in light mode and offers dark mode', () => {
    render(<ThemeToggle />)
    expect(screen.getByRole('button', { name: 'Switch to dark mode' })).toBeInTheDocument()
  })

  it('switches the theme and the html class, then back', () => {
    render(<ThemeToggle />)
    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark mode' }))
    expect(useThemeStore.getState().dark).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(true)

    fireEvent.click(screen.getByRole('button', { name: 'Switch to light mode' }))
    expect(useThemeStore.getState().dark).toBe(false)
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('defaults the store to light', () => {
    localStorage.clear()
    expect(useThemeStore.getInitialState().dark).toBe(false)
  })
})
