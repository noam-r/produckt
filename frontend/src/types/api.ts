/**
 * Type definitions for API responses
 * These should match the backend Pydantic schemas
 */

// Auth types
export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  organization_id: string;
  organization_name: string;
}

export interface LoginResponse {
  session_id: string;
  user_id: string;
  email: string;
  name: string;
  role: string;
  organization_id: string;
  organization_name: string;
  expires_at: string;
}

export interface SessionResponse extends LoginResponse {}

// Initiative types
export interface Initiative {
  id: string;
  title: string;  // NOTE: Backend uses 'title', not 'name'
  description: string;
  status: InitiativeStatus;
  readiness_score?: number;
  iteration_count: number;
  organization_id: string;
  created_by: string;
  context_snapshot_id?: string;
  created_at: string;
  updated_at: string;
}

export type InitiativeStatus =
  | 'Draft'
  | 'In_QA'
  | 'Ready'
  | 'MRD_Generated'
  | 'Scored'
  | 'Archived';

export interface InitiativeListResponse {
  initiatives: Initiative[];
  total: number;
  limit: number;
  offset: number;
}

export interface InitiativeCreate {
  title: string;
  description: string;
}

export interface InitiativeUpdate {
  title?: string;
  description?: string;
  status?: InitiativeStatus;
}

// Question types
export interface Question {
  id: string;
  initiative_id: string;
  question_text: string;
  question_type: string;
  iteration: number;
  created_at: string;
}

// Answer types
export interface Answer {
  id: string;
  question_id: string;
  answer_text: string;
  answered_by: string;
  created_at: string;
}

// MRD types
export interface MRD {
  id: string;
  initiative_id: string;
  content: string;
  version: number;
  created_at: string;
}

// Score types
export interface Score {
  id: string;
  initiative_id: string;
  category: string;
  score: number;
  reasoning: string;
  created_at: string;
}

// Context types
export interface Context {
  id: string;
  organization_id: string;
  company_mission?: string;
  strategic_objectives?: string;
  target_markets?: string;
  competitive_landscape?: string;
  technical_constraints?: string;
  version: number;
  is_current: boolean;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface ContextListResponse {
  contexts: Context[];
  total: number;
}

export interface ContextCreate {
  company_mission?: string;
  strategic_objectives?: string;
  target_markets?: string;
  competitive_landscape?: string;
  technical_constraints?: string;
}
