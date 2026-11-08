import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges
} from '@angular/core';

import { HttpErrorResponse } from '@angular/common/http';
import { Subscription } from 'rxjs';
import { finalize } from 'rxjs/operators';

import {
  AppService,
  Language,
  OCRSource,
  PatientExplanationResult
} from '../../app.service';


type Assessment =
  | 'understood'
  | 'partially_understood'
  | 'needs_clarification'
  | 'not_assessable';


interface TeachBackEvidence extends OCRSource {
  fact_id: string;
}


interface TeachBackQuestion {
  question_id: string;
  question: string;
  fact_ids: string[];
  evidence: TeachBackEvidence[];
}


interface TeachBackGenerateResponse {
  status: string;
  language: Language;
  total_questions: number;
  questions: TeachBackQuestion[];
}


interface TeachBackEvaluationResponse {
  status: string;
  language: Language;
  question_id: string;
  assessment: Assessment;
  feedback: string;
  clarification: string | null;
  supporting_fact_ids: string[];
  evidence: TeachBackEvidence[];
}


@Component({
  selector: 'app-teachback',
  templateUrl: './teachback.component.html',
  styleUrls: ['./teachback.component.scss']
})
export class TeachbackComponent implements OnChanges, OnDestroy {

  @Input() explanation: PatientExplanationResult | null = null;

  @Output() sourceSelected = new EventEmitter<OCRSource>();

  questions: TeachBackQuestion[] = [];

  currentQuestionIndex = 0;
  answer = '';

  evaluation: TeachBackEvaluationResponse | null = null;

  isGenerating = false;
  isEvaluating = false;
  isComplete = false;

  errorMessage = '';

  private generateSubscription?: Subscription;
  private evaluateSubscription?: Subscription;

  constructor(
    private appService: AppService
  ) {}

  /**
   * Reset Teach-Back whenever a new document
   * analysis is received.
   */
  ngOnChanges(changes: SimpleChanges): void {
    if (changes['explanation']) {
      this.cancelRequests();
      this.reset();
    }
  }

  /**
   * Return the currently displayed question.
   */
  get currentQuestion(): TeachBackQuestion | null {
    return this.questions[this.currentQuestionIndex] || null;
  }

  /**
   * Prepare the explanation facts expected by
   * the Teach-Back backend.
   */
  private prepareFacts() {
    return (this.explanation?.explanations || [])
      .slice(0, 40)
      .map(fact => ({
        fact_id: fact.fact_id,
        label: fact.label,
        value: fact.value,
        explanation: fact.explanation,
        needs_review: fact.needs_review,
        review_reasons: fact.review_reasons,
        source: fact.source
      }));
  }

  /**
   * Generate questions using Gemini.
   */
  start(): void {
    if (!this.explanation || this.isGenerating) {
      return;
    }

    const facts = this.prepareFacts();

    if (!facts.length) {
      this.errorMessage = 'No medical information is available.';
      return;
    }

    this.cancelRequests();
    this.reset();

    this.isGenerating = true;

    const payload = {
      language: this.explanation.language,
      question_count: Math.min(2, facts.length),
      explanations: facts
    };

    this.generateSubscription = this.appService
      .generateTeachBack<TeachBackGenerateResponse>(payload)
      .pipe(
        finalize(() => {
          this.isGenerating = false;
        })
      )
      .subscribe({
        next: (response) => {
          if (
            response.status !== 'success' ||
            !Array.isArray(response.questions) ||
            response.questions.length === 0
          ) {
            this.errorMessage = 'No questions were generated.';
            return;
          }

          this.questions = response.questions;
          this.currentQuestionIndex = 0;
        },
        error: (error) => {
          this.errorMessage = this.getErrorMessage(error);
        }
      });
  }

  /**
   * Update the user's answer.
   */
  onAnswerInput(event: Event): void {
    const textarea = event.target as HTMLTextAreaElement;
    this.answer = textarea.value;
  }

  /**
   * Evaluate the current answer using Gemini.
   */
  evaluate(): void {
    const question = this.currentQuestion;

    if (
      !this.explanation ||
      !question ||
      !this.answer.trim() ||
      this.isEvaluating ||
      this.evaluation
    ) {
      return;
    }

    this.isEvaluating = true;
    this.errorMessage = '';

    const payload = {
      language: this.explanation.language,
      explanations: this.prepareFacts(),
      question: {
        question_id: question.question_id,
        question: question.question,
        fact_ids: question.fact_ids
      },
      answer: this.answer.trim()
    };

    this.evaluateSubscription = this.appService
      .evaluateTeachBack<TeachBackEvaluationResponse>(payload)
      .pipe(
        finalize(() => {
          this.isEvaluating = false;
        })
      )
      .subscribe({
        next: (response) => {
          if (
            response.status !== 'success' ||
            response.question_id !== question.question_id
          ) {
            this.errorMessage = 'Invalid evaluation response.';
            return;
          }

          this.evaluation = response;
        },
        error: (error) => {
          this.errorMessage = this.getErrorMessage(error);
        }
      });
  }

  /**
   * Move to the next question after receiving feedback.
   */
  nextQuestion(): void {
    if (!this.evaluation) {
      return;
    }

    if (this.currentQuestionIndex + 1 >= this.questions.length) {
      this.isComplete = true;
      return;
    }

    this.currentQuestionIndex++;
    this.answer = '';
    this.evaluation = null;
    this.errorMessage = '';
  }

  /**
   * Show the original OCR source in DocumentViewer.
   */
  viewEvidence(evidence: TeachBackEvidence): void {
    this.sourceSelected.emit({
      page_index: evidence.page_index,
      source_line_index: evidence.source_line_index,
      source_quote: evidence.source_quote
    });
  }

  /**
   * Convert assessment codes into readable labels.
   */
  getAssessmentLabel(assessment: Assessment): string {
    const labels: Record<Assessment, string> = {
      understood: 'Understood',
      partially_understood: 'Partially understood',
      needs_clarification: 'Needs clarification',
      not_assessable: 'Not assessable'
    };

    return labels[assessment];
  }

  /**
   * Reset local Teach-Back state.
   */
  private reset(): void {
    this.questions = [];
    this.currentQuestionIndex = 0;
    this.answer = '';
    this.evaluation = null;
    this.isGenerating = false;
    this.isEvaluating = false;
    this.isComplete = false;
    this.errorMessage = '';
  }

  private cancelRequests(): void {
    this.generateSubscription?.unsubscribe();
    this.evaluateSubscription?.unsubscribe();
  }

  private getErrorMessage(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      if (error.status === 0) {
        return 'Cannot connect to the backend API.';
      }

      if (error.status === 502) {
        return 'AI processing failed. Please try again.';
      }

      return `Request failed (HTTP ${error.status}).`;
    }

    return 'An unexpected error occurred.';
  }

  ngOnDestroy(): void {
    this.cancelRequests();
  }
}