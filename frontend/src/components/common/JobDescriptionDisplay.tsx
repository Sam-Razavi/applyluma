import { parseJobDescription } from '../../utils/jobDescription'

interface Props {
  raw: string
  className?: string
}

export default function JobDescriptionDisplay({ raw, className = '' }: Props) {
  const blocks = parseJobDescription(raw)

  if (blocks.length === 0) return null

  return (
    <div className={`space-y-3 text-sm leading-relaxed text-fg-muted ${className}`}>
      {blocks.map((block, i) => {
        switch (block.kind) {
          case 'heading':
            return (
              <h4 key={i} className="mt-4 font-semibold text-fg first:mt-0">
                {block.text}
              </h4>
            )
          case 'paragraph':
            return (
              <p key={i} className="break-words">
                {block.text}
              </p>
            )
          case 'bullet':
            return (
              <ul key={i} className="list-disc list-outside space-y-1 pl-5">
                {block.items.map((item, j) => (
                  <li key={j} className="break-words">{item}</li>
                ))}
              </ul>
            )
          case 'numbered':
            return (
              <ol key={i} className="list-decimal list-outside space-y-1 pl-5">
                {block.items.map((item, j) => (
                  <li key={j} className="break-words">{item}</li>
                ))}
              </ol>
            )
        }
      })}
    </div>
  )
}
