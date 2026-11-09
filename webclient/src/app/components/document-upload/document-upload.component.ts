import {
  Component,
  EventEmitter,
  Output
} from '@angular/core';

import { finalize } from 'rxjs/operators';

import { AppService, Language } from '../../app.service';
import { LanguageService } from '../../services/language.service';


interface ImagePreview {
  name: string;
  url: string;
  size: number;
}


@Component({
  selector: 'app-document-upload',
  templateUrl: './document-upload.component.html',
  styleUrls: ['./document-upload.component.scss']
})
export class DocumentUploadComponent {

  @Output() analysisCompleted = new EventEmitter<{
    result: unknown;
    files: File[];
  }>();

  selectedFiles: File[] = [];
  previews: ImagePreview[] = [];

  language: Language = 'en';

  isLoading = false;

  // Store translation keys so errors update when the UI language changes.
  private errorKey = '';
  private errorDetail = '';

  get errorMessage(): string {
    if (!this.errorKey) {
      return '';
    }

    return this.i18n.translate(this.errorKey).replace(
      '{detail}',
      this.errorDetail
    );
  }

  private setError(key: string, detail = ''): void {
    this.errorKey = key;
    this.errorDetail = detail;
  }

  private clearError(): void {
    this.errorKey = '';
    this.errorDetail = '';
  }

  private readonly maxFiles = 12;
  private readonly maxFileSize = 5 * 1024 * 1024;
  private readonly maxTotalSize = 25 * 1024 * 1024;

  private readonly allowedTypes = [
    'image/jpeg',
    'image/png'
  ];

  constructor(
    private appService: AppService,
    public readonly i18n: LanguageService
  ) { }

  /**
   * Handle image selection and generate previews.
   */
  onFilesSelected(event: Event): void {

    if (this.isLoading) {
      return;
    }

    const input = event.target as HTMLInputElement;

    const files = Array.from(
      input.files || []
    );

    // Allow selecting the same file again.
    input.value = '';

    if (files.length === 0) {
      return;
    }

    this.clearError();

    // Validate number of images.
    if (files.length > this.maxFiles) {
      this.setError('upload.error.maxFiles');
      return;
    }

    // Validate MIME types.
    const invalidFile = files.find(
      file => !this.allowedTypes.includes(file.type)
    );

    if (invalidFile) {
      this.setError('upload.error.invalidType');
      return;
    }

    // Validate individual file sizes.
    const oversizedFile = files.find(
      file => file.size > this.maxFileSize
    );

    if (oversizedFile) {
      this.setError('upload.error.fileSize');
      return;
    }

    // Validate total upload size.
    const totalSize = files.reduce(
      (total, file) => total + file.size,
      0
    );

    if (totalSize > this.maxTotalSize) {
      this.setError('upload.error.totalSize');
      return;
    }

    // Save selected files.
    this.selectedFiles = files;

    // Initialize preview list.
    this.previews = files.map(file => ({
      name: file.name,
      url: '',
      size: file.size
    }));

    // Generate image previews with FileReader.
    files.forEach((file, index) => {

      const reader = new FileReader();

      reader.onload = () => {

        // Ignore callbacks from previous selections.
        if (
          this.selectedFiles[index] !== file ||
          !reader.result
        ) {
          return;
        }

        this.previews[index].url = (
          reader.result as string
        );
      };

      reader.onerror = () => {
        if (this.selectedFiles[index] === file) {
          this.setError('upload.error.preview', file.name);
        }
      };

      reader.readAsDataURL(file);

    });
  }

  /**
   * Update selected explanation language.
   */
  onLanguageChange(event: Event): void {

    const select = event.target as HTMLSelectElement;

    this.language = select.value as Language;
  }

  /**
   * Call the Unified Analysis API.
   */
  analyze(): void {

    if (
      this.selectedFiles.length === 0 ||
      this.isLoading
    ) {
      return;
    }

    this.isLoading = true;
    this.clearError();

    this.appService
      .analyzeDocuments<unknown>(
        this.selectedFiles,
        this.language
      )
      .pipe(
        finalize(() => {
          this.isLoading = false;
        })
      )
      .subscribe({

        next: (result) => {

          console.log(
            'ClinPlain analysis completed.'
          );

          this.analysisCompleted.emit({
            result: result,
            files: [...this.selectedFiles]
          });
        },

        error: (error) => {

          const stage = error.error?.detail?.stage;

          if (stage) {

            this.setError('upload.error.stage', String(stage));

          } else if (error.status === 429) {

            this.setError('upload.error.rateLimit');

          } else if (error.status === 0) {

            this.setError('upload.error.connection');

          } else {

            this.setError('upload.error.generic');
          }

          console.error(
            'Document analysis failed:',
            error.status,
            stage || 'unknown'
          );
        }
      });
  }

  /**
   * Remove selected files and previews.
   */
  clearFiles(): void {

    if (this.isLoading) {
      return;
    }

    this.selectedFiles = [];
    this.previews = [];
    this.clearError();
  }
}