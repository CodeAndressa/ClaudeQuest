export interface TrackSummary {
  id: string
  title: string
  description: string
  difficulty: string
  estimated_hours: number
  total_lessons: number
  completed_lessons: number
  progress_percent: number
  image: string | null
  icon: string | null
  order: number
}

export interface AlternativeDetail {
  id: string
  text: string
  is_correct: boolean
  feedback: string | null
  order: number
}

export interface QuestionDetail {
  id: string
  question: string
  question_type: string
  explanation: string | null
  points: number
  order: number
  alternatives: AlternativeDetail[]
}

export interface LessonDetail {
  id: string
  title: string
  description: string
  content: string
  estimated_minutes: number
  difficulty: string
  lesson_type: string
  order: number
  xp: number
  ai_corrected: boolean
  completed: boolean
  questions: QuestionDetail[]
}

export interface LevelDetail {
  id: string
  title: string
  description: string
  level_number: number
  estimated_minutes: number
  xp: number
  stars: number
  required_xp: number
  lessons: LessonDetail[]
}

export interface ModuleDetail {
  id: string
  title: string
  description: string
  order: number
  levels: LevelDetail[]
}

export interface TrackDetail {
  id: string
  title: string
  description: string
  difficulty: string
  estimated_hours: number
  total_lessons: number
  completed_lessons: number
  progress_percent: number
  image: string | null
  icon: string | null
  order: number
  is_active: boolean
  modules: ModuleDetail[]
}

export interface CompleteLessonResponse {
  lesson_id: string
  completed: boolean
  already_completed: boolean
  xp_granted: number
  total_xp: number
  level: number
  xp_to_next_level: number
}
