import type { Story } from '../types'
import { Draggable } from '@hello-pangea/dnd'

const priorityBorder: Record<string, string> = {
  high: 'border-l-red-500',
  medium: 'border-l-amber-400',
  low: 'border-l-slate-300',
}
const priorityLabel: Record<string, string> = { high: 'P1', medium: 'P2', low: 'P3' }

interface Props {
  story: Story
  index: number
  onClick: (story: Story) => void
}

export default function StoryCard({ story, index, onClick }: Props) {
  return (
    <Draggable draggableId={String(story.id)} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          onClick={() => onClick(story)}
          className={[
            'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700',
            'border-l-4', priorityBorder[story.priority],
            'rounded-lg p-3 mb-2 cursor-pointer shadow-sm hover:shadow-md transition-all duration-150',
            snapshot.isDragging ? 'opacity-80 shadow-lg rotate-1' : ''
          ].join(' ')}
        >
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 leading-snug mb-2">{story.title}</p>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {story.assignee_name && (
                <span
                  className="w-5 h-5 rounded-full text-white text-xs flex items-center justify-center font-mono font-bold"
                  style={{ backgroundColor: story.assignee_color || '#94A3B8' }}
                  title={story.assignee_name}
                >
                  {story.assignee_name[0].toUpperCase()}
                </span>
              )}
            </div>
            <span className="text-xs font-mono text-slate-400 dark:text-slate-500">{priorityLabel[story.priority]}</span>
          </div>
        </div>
      )}
    </Draggable>
  )
}
