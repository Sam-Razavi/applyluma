import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { TemplatePicker } from './TemplatePicker'

describe('TemplatePicker', () => {
  it('renders both templates with the current selection pressed', () => {
    render(<TemplatePicker value="nordic" onChange={() => undefined} />)

    const nordic = screen.getByRole('button', { name: /nordic/i })
    const classic = screen.getByRole('button', { name: /classic/i })
    expect(nordic).toHaveAttribute('aria-pressed', 'true')
    expect(classic).toHaveAttribute('aria-pressed', 'false')
  })

  it('calls onChange with the clicked template id', () => {
    const onChange = vi.fn()
    render(<TemplatePicker value="nordic" onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: /classic/i }))
    expect(onChange).toHaveBeenCalledWith('classic')
  })
})
