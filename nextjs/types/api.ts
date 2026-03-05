export type User = {
  id: number;
  name: string;
  email: string;
  xp: number;
  subscription_status: 'pro' | 'trial' | null;
  trial_ends_at: string | null;
  is_pro: boolean;
};

export type Domain = {
  id: number;
  name: string;
  slug: string;
  description: string;
  order: number;
  lesson_count?: number;
};

export type UserProgress = {
  lesson_id: number;
  completed_at: string | null;
  time_spent_seconds: number;
};

export type Question = {
  id: number;
  lesson_id: number;
  stem: string;
  options: string[];
  difficulty: 'easy' | 'medium' | 'hard';
};

export type Lesson = {
  id: number;
  domain_id: number;
  title: string;
  slug: string;
  content: string;
  order: number;
  is_free: boolean;
  question_count?: number;
  questions?: Question[];
  user_progress?: UserProgress | null;
};

export type QuestionAttempt = {
  id: number;
  question_id: number;
  selected_option: number;
  is_correct: boolean;
  correct_option: number;
  explanation: string;
  explained_at: string | null;
};

export type Streak = {
  current_streak: number;
  longest_streak: number;
  last_activity_date: string | null;
};

export type Progress = {
  completed_lessons: number;
  progress: UserProgress[];
};

/** Laravel API wraps all responses in { data: T } */
export type ApiResponse<T> = { data: T };
