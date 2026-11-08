import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export type Language = 'vi' | 'en' | 'ja';
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

@Injectable({
  providedIn: 'root'
})
export class AppService {

  private readonly http = inject(HttpClient);

  private readonly baseUrl = 'http://localhost:8000';

  /**
   * Common HTTP request method.
   */
  private callApi<T>(
    method: HttpMethod,
    endpoint: string,
    body?: unknown
  ): Observable<T> {

    return this.http.request<T>(
      method,
      `${this.baseUrl}${endpoint}`,
      { body }
    );
  }

  /**
   * Upload medical documents and run full analysis.
   */
  analyzeDocuments<T>(
    files: File[],
    language: Language = 'vi'
  ): Observable<T> {

    const formData = new FormData();

    files.forEach(file => {
      formData.append('files', file);
    });

    formData.append('language', language);

    return this.callApi<T>(
      'POST',
      '/api/documents/analyze',
      formData
    );
  }

  /**
   * Generate teach-back questions.
   */
  generateTeachBack<T>(
    payload: unknown
  ): Observable<T> {

    return this.callApi<T>(
      'POST',
      '/api/teachback/generate',
      payload
    );
  }

  /**
   * Evaluate a teach-back answer.
   */
  evaluateTeachBack<T>(
    payload: unknown
  ): Observable<T> {

    return this.callApi<T>(
      'POST',
      '/api/teachback/evaluate',
      payload
    );
  }
}

export interface OCRSource {
  page_index: number;
  source_line_index: number;
  source_quote: string;
}

export interface LinkedText {
  text: string;
  fact_ids: string[];
}

export interface MedicalExplanation {
  fact_id: string;
  label: string;
  value: string | null;
  unit: string | null;

  fhir_hint: string;
  fhir_status: string;

  needs_review: boolean;
  review_reasons: string[];
  fhir_mapping_notes?: string[];

  source: OCRSource;
  explanation: string;
}

export interface PatientExplanationResult {
  status: string;
  language: Language;

  summary: LinkedText | null;
  explanations: MedicalExplanation[];
  clinician_questions: LinkedText[];

  disclaimer: string;
  message?: string;
}

export interface AnalysisResult {
  status: string;
  language: Language;
  total_pages: number;

  ocr: {
    status: string;
    total_pages: number;
    pages: OCRPage[];
  };

  explanation: PatientExplanationResult;
}

export interface OCRPoint {
  x: number;
  y: number;
}

export interface OCRLine {
  text: string;
  confidence: number | null;
  bounding_box: OCRPoint[];
}

export interface OCRPage {
  page_index: number;
  filename: string;
  text: string;
  lines: OCRLine[];
}