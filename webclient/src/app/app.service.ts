import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, defer, switchMap } from 'rxjs';

import { initializeApp } from 'firebase/app';

import {
  AppCheck,
  initializeAppCheck,
  ReCaptchaEnterpriseProvider,
  getToken
} from 'firebase/app-check';

import { environment } from '../environments/environment';


export type Language = 'en' | 'ja' | 'vi';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';


@Injectable({
  providedIn: 'root'
})
export class AppService {

  private readonly http = inject(HttpClient);

  private readonly baseUrl = environment.apiUrl;

  private readonly appCheck: AppCheck | null;


  constructor() {

    // App Check is enabled only in production.
    // Local development continues to use localhost:8000.

    if (environment.production) {

      const firebaseApp = initializeApp(
        environment.firebaseConfig
      );

      this.appCheck = initializeAppCheck(firebaseApp, {
        provider: new ReCaptchaEnterpriseProvider(
          environment.recaptchaEnterpriseSiteKey
        ),
        isTokenAutoRefreshEnabled: true
      });

    } else {

      this.appCheck = null;

    }
  }


  /**
   * Common HTTP request method.
   *
   * Production:
   *   Firebase App Check token -> FastAPI request
   *
   * Development:
   *   Direct request to local FastAPI
   */
  private callApi<T>(
    method: HttpMethod,
    endpoint: string,
    body?: unknown
  ): Observable<T> {

    const url = `${this.baseUrl}${endpoint}`;

    // Development: no App Check token required.
    if (!this.appCheck) {

      return this.http.request<T>(
        method,
        url,
        { body }
      );
    }

    const appCheck = this.appCheck;

    // Production: obtain an App Check token before
    // sending each request.
    return defer(() => getToken(appCheck)).pipe(

      switchMap(({ token }) => {

        const headers = new HttpHeaders({
          'X-Firebase-AppCheck': token
        });

        return this.http.request<T>(
          method,
          url,
          {
            body,
            headers
          }
        );
      })
    );
  }


  /**
   * Upload medical documents and run full analysis.
   */
  analyzeDocuments<T>(
    files: File[],
    language: Language = 'en'
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
   * Generate Teach-Back questions.
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
   * Evaluate a Teach-Back answer.
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