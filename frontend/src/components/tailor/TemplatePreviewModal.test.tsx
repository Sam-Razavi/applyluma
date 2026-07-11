import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { TemplatePreviewModal } from './TemplatePreviewModal'

describe('TemplatePreviewModal', () => {
  const fetchHtml = vi.fn()
  const onClose = vi.fn()
  const onTemplateChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches and renders the preview iframe when opened', async () => {
    fetchHtml.mockResolvedValue('<html><body>My CV</body></html>')
    render(
      <TemplatePreviewModal
        open
        templateId="nordic"
        onClose={onClose}
        onTemplateChange={onTemplateChange}
        fetchHtml={fetchHtml}
      />,
    )

    expect(fetchHtml).toHaveBeenCalledWith('nordic')
    const iframe = await screen.findByTitle<HTMLIFrameElement>('CV preview')
    expect(iframe).toBeInTheDocument()
    expect(iframe.getAttribute('srcdoc')).toContain('My CV')
    expect(iframe.getAttribute('sandbox')).toBe('')
  })

  it('shows a loading state while fetching', () => {
    fetchHtml.mockReturnValue(new Promise(() => undefined))
    render(
      <TemplatePreviewModal
        open
        templateId="nordic"
        onClose={onClose}
        onTemplateChange={onTemplateChange}
        fetchHtml={fetchHtml}
      />,
    )

    expect(screen.getByRole('status', { name: /loading preview/i })).toBeInTheDocument()
  })

  it('switching template calls onTemplateChange with the new id', async () => {
    fetchHtml.mockResolvedValue('<html></html>')
    render(
      <TemplatePreviewModal
        open
        templateId="nordic"
        onClose={onClose}
        onTemplateChange={onTemplateChange}
        fetchHtml={fetchHtml}
      />,
    )
    await screen.findByTitle('CV preview')

    fireEvent.click(screen.getByRole('button', { name: 'Executive' }))
    expect(onTemplateChange).toHaveBeenCalledWith('executive')
  })

  it('re-fetches when the templateId prop changes', async () => {
    fetchHtml.mockResolvedValue('<html></html>')
    const { rerender } = render(
      <TemplatePreviewModal
        open
        templateId="nordic"
        onClose={onClose}
        onTemplateChange={onTemplateChange}
        fetchHtml={fetchHtml}
      />,
    )
    await screen.findByTitle('CV preview')

    rerender(
      <TemplatePreviewModal
        open
        templateId="modern"
        onClose={onClose}
        onTemplateChange={onTemplateChange}
        fetchHtml={fetchHtml}
      />,
    )
    await waitFor(() => expect(fetchHtml).toHaveBeenCalledWith('modern'))
  })

  it('shows an error state with retry when the fetch fails', async () => {
    fetchHtml.mockRejectedValueOnce(new Error('boom'))
    fetchHtml.mockResolvedValueOnce('<html><body>Recovered</body></html>')
    render(
      <TemplatePreviewModal
        open
        templateId="nordic"
        onClose={onClose}
        onTemplateChange={onTemplateChange}
        fetchHtml={fetchHtml}
      />,
    )

    expect(await screen.findByText(/could not load the preview/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    const iframe = await screen.findByTitle<HTMLIFrameElement>('CV preview')
    expect(iframe.getAttribute('srcdoc')).toContain('Recovered')
  })
})
