import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ConfirmDialog from './ConfirmDialog'

describe('ConfirmDialog', () => {
  it('confirm button is enabled by default (no requireText)', () => {
    const onConfirm = vi.fn()
    render(
      <ConfirmDialog
        open
        title="Delete item?"
        message="This cannot be undone."
        onCancel={vi.fn()}
        onConfirm={onConfirm}
      />
    )
    const confirmButton = screen.getByRole('button', { name: 'Delete' })
    expect(confirmButton).not.toBeDisabled()
    fireEvent.click(confirmButton)
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('disables confirm until the required text is typed exactly', () => {
    const onConfirm = vi.fn()
    render(
      <ConfirmDialog
        open
        title="Delete user?"
        message="Type the email to confirm."
        requireText="user@example.com"
        onCancel={vi.fn()}
        onConfirm={onConfirm}
      />
    )
    const confirmButton = screen.getByRole('button', { name: 'Delete' })
    expect(confirmButton).toBeDisabled()

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'wrong@example.com' } })
    expect(confirmButton).toBeDisabled()

    fireEvent.change(input, { target: { value: 'user@example.com' } })
    expect(confirmButton).not.toBeDisabled()

    fireEvent.click(confirmButton)
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('clears the typed text when cancelled', () => {
    const onCancel = vi.fn()
    const { rerender } = render(
      <ConfirmDialog
        open
        title="Delete user?"
        message="Type the email to confirm."
        requireText="user@example.com"
        onCancel={onCancel}
        onConfirm={vi.fn()}
      />
    )
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'user@example.com' } })
    expect(screen.getByRole('button', { name: 'Delete' })).not.toBeDisabled()

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onCancel).toHaveBeenCalledTimes(1)

    rerender(
      <ConfirmDialog
        open
        title="Delete user?"
        message="Type the email to confirm."
        requireText="user@example.com"
        onCancel={onCancel}
        onConfirm={vi.fn()}
      />
    )
    expect(screen.getByRole('textbox')).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Delete' })).toBeDisabled()
  })
})
