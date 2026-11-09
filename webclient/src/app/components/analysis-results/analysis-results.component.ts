import {
  Component,
  Input,
  Output,
  EventEmitter,
  OnChanges,
  SimpleChanges
} from '@angular/core';

import {
  AnalysisResult,
  MedicalExplanation,
  OCRSource
} from '../../app.service';
import { LanguageService } from '../../services/language.service';


@Component({
  selector: 'app-analysis-results',
  templateUrl: './analysis-results.component.html',
  styleUrls: ['./analysis-results.component.scss']
})
export class AnalysisResultsComponent implements OnChanges {

  constructor(public readonly i18n: LanguageService) { }

  @Input() result: AnalysisResult | null = null;

  @Output() sourceSelected = new EventEmitter<OCRSource | null>();

  expandedFactId: string | null = null;

  /**
   * Reset selected evidence when a new analysis arrives.
   */
  ngOnChanges(changes: SimpleChanges): void {
    if (changes['result']) {
      this.expandedFactId = null;
    }
  }

  /**
   * Expand or collapse the original OCR evidence.
   */
  toggleSource(fact: MedicalExplanation): void {

    const isExpanded = this.expandedFactId === fact.fact_id;

    this.expandedFactId = isExpanded
      ? null
      : fact.fact_id;

    this.sourceSelected.emit(
      isExpanded ? null : fact.source
    );
  }

  /**
   * Keep fact cards stable during Angular rendering.
   */
  trackByFactId(
    index: number,
    fact: MedicalExplanation
  ): string {
    return fact.fact_id;
  }
}