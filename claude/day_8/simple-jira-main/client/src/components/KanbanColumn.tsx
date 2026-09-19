import { Droppable } from '@hello-pangea/dnd'
import type { Story, Status } from '../types'
import StoryCard from './StoryCard'

const columnConfig: Record<Status, { label: string; accent: string }> = {
  backlog:     { label: 'Backlog',     accent: 'border-t-slate-400' },
  in_progress: { label: 'In Progress', accent: 'border-t-indigo-500' },
  review:      { label: 'Review',      accent: 'border-t-amber-400' },
  done:        { label: 'Done',        accent: 'border-t-green-500' },
}

interface Props {
  status: Status
  stories: Story[]
  onCardClick: (story: Story) => void
}

export default function KanbanColumn({ status, stories, onCardClick }: Props) {
  const { label, accent } = columnConfig[status]
  return (
    <div className={'flex-1 min-w-[260px] max-w-[320px] bg-slate-100 dark:bg-slate-800/50 border-t-4 ' + accent + ' rounded-xl p-3 flex flex-col'}>
      <div className="flex items-center justify-between mb-3 px-1">
        <h2 className="font-mono font-semibold text-sm text-slate-700 dark:text-slate-300 uppercase tracking-wide">{label}</h2>
        <span className="font-mono text-xs bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400 rounded-full px-2 py-0.5">{stories.length}</span>
      </div>
      <Droppable droppableId={status}>
        {(provided, snapshot) => (
          <div
            ref={provided.innerRef}
            {...provided.droppableProps}
            className={'flex-1 min-h-[120px] rounded-lg transition-colors duration-150' + (snapshot.isDraggingOver ? ' bg-indigo-50 dark:bg-indigo-900/20 border-2 border-dashed border-indigo-300 dark:border-indigo-700' : '')}
          >
            {stories.map((story, index) => (
              <StoryCard key={story.id} story={story} index={index} onClick={onCardClick} />
            ))}
            {stories.length === 0 && !snapshot.isDraggingOver && (
              <p className="text-xs font-mono text-slate-400 dark:text-slate-600 text-center pt-6 pb-2">Drop cards here</p>
            )}
            {provided.placeholder}
          </div>
        )}
      </Droppable>
    </div>
  )
}
