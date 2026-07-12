import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { TemplatePicker } from './TemplatePicker'

describe('TemplatePicker', () => {
  it('renders all templates with the current selection pressed', () => {
    render(<TemplatePicker value="nordic" onChange={() => undefined} />)

    const nordic = screen.getByRole('button', { name: /^nordic/i })
    const classic = screen.getByRole('button', { name: /^classic/i })
    const modern = screen.getByRole('button', { name: /^modern/i })
    const executive = screen.getByRole('button', { name: /^executive/i })
    const atlas = screen.getByRole('button', { name: /^atlas/i })
    const compact = screen.getByRole('button', { name: /^compact/i })
    expect(nordic).toHaveAttribute('aria-pressed', 'true')
    expect(classic).toHaveAttribute('aria-pressed', 'false')
    expect(modern).toHaveAttribute('aria-pressed', 'false')
    expect(executive).toHaveAttribute('aria-pressed', 'false')
    expect(atlas).toHaveAttribute('aria-pressed', 'false')
    expect(compact).toHaveAttribute('aria-pressed', 'false')
  })

  it('calls onChange with the clicked template id', () => {
    const onChange = vi.fn()
    render(<TemplatePicker value="nordic" onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: /^classic/i }))
    expect(onChange).toHaveBeenCalledWith('classic')
  })

  it('calls onChange for the new modern and executive templates', () => {
    const onChange = vi.fn()
    render(<TemplatePicker value="nordic" onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: /^modern/i }))
    expect(onChange).toHaveBeenCalledWith('modern')

    fireEvent.click(screen.getByRole('button', { name: /^executive/i }))
    expect(onChange).toHaveBeenCalledWith('executive')
  })

  it('calls onChange for the new atlas and compact templates', () => {
    const onChange = vi.fn()
    render(<TemplatePicker value="nordic" onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: /^atlas/i }))
    expect(onChange).toHaveBeenCalledWith('atlas')

    fireEvent.click(screen.getByRole('button', { name: /^compact/i }))
    expect(onChange).toHaveBeenCalledWith('compact')
  })
})
