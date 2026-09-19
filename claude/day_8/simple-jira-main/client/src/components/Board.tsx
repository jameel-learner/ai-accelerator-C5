import { DragDropContext } from '@hello-pangea/dnd'
import type { DropResult } from '@hello-pangea/dnd'
import type { Status, Story } from '../types'
import { useStories } from '../hooks/useStories'
import KanbanColumn from './KanbanColumn'

const COLUMNS: Status[] = ['backlog', 'in_progress', 'review', 'done']

interface Props {
  onCardClick: (story: Story) => void
}

export default function Board({ onCardClick }: Props) {
  const { loading, storiesByStatus, moveStory } = useStories()

  const onDragEnd = (result: DropResult) => {
    const { destination, source, draggableId } = result
    if (!destination) return
    if (destination.droppableId === source.droppableId && destination.index === source.index) return
    moveStory(parseInt(draggableId), destination.droppableId as Status, destination.index)
  }

  if (loading) {
    return (
      <div className="flex gap-4 p-6 overflow-x-auto">
        {COLUMNS.map(col => (
          <div key={col} className="flex-1 min-w-[260px] max-w-[320px] h-48 bg-slate-100 dark:bg-slate-800/50 rounded-xl animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <div className="flex gap-4 p-6 overflow-x-auto min-h-[calc(100vh-80px)]">
        {COLUMNS.map(status => (
          <KanbanColumn key={status} status={status} stories={storiesByStatus(status)} onCardClick={onCardClick} />
        ))}
      </div>
    </DragDropContext>
  )
}
