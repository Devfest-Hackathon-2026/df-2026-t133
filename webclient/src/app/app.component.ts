import { Component } from '@angular/core';
import { LanguageService, UiLanguage } from './services/language.service';

import {
  AnalysisResult,
  OCRSource
} from './app.service';


@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {

  constructor(public readonly languageService: LanguageService) {}

  setUiLanguage(language: UiLanguage): void {
    this.languageService.setLanguage(language);
  }

  analysisResult: AnalysisResult | null = null;

  uploadedFiles: File[] = [];

  selectedSource: OCRSource | null = null;

  /**
   * Receive the unified analysis result.
   */
  onAnalysisCompleted(event: {
    result: unknown;
    files: File[];
  }): void {

    const result = event.result as AnalysisResult;

    if (!result || !result.explanation || !result.ocr) {
      console.error('Invalid ClinPlain analysis response.');
      return;
    }

    this.analysisResult = result;

    this.uploadedFiles = event.files;

    // Clear any source from the previous analysis.
    this.selectedSource = null;
  }

  /**
   * Handle source selection from AnalysisResultsComponent.
   */
  onSourceSelected(source: OCRSource | null): void {
    this.selectedSource = source;
  }

  onTeachBackSourceSelected(source: OCRSource): void {
    this.onSourceSelected(source);

    document
      .getElementById('analysis-workspace')
      ?.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
  }
}