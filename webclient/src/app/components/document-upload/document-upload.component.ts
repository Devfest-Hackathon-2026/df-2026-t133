import {
  Component,
  EventEmitter,
  Output
} from '@angular/core';

import { finalize } from 'rxjs/operators';

import { AppService, Language } from '../../app.service';


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

  language: Language = 'vi';

  isLoading = false;
  errorMessage = '';

  private readonly maxFiles = 12;
  private readonly maxFileSize = 5 * 1024 * 1024;
  private readonly maxTotalSize = 25 * 1024 * 1024;

  private readonly allowedTypes = [
    'image/jpeg',
    'image/png'
  ];

  constructor(
    private appService: AppService
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

    this.errorMessage = '';

    // Validate number of images.
    if (files.length > this.maxFiles) {
      this.errorMessage = (
        'Maximum 12 images allowed.'
      );
      return;
    }

    // Validate MIME types.
    const invalidFile = files.find(
      file => !this.allowedTypes.includes(file.type)
    );

    if (invalidFile) {
      this.errorMessage = (
        'Only JPEG and PNG images are supported.'
      );
      return;
    }

    // Validate individual file sizes.
    const oversizedFile = files.find(
      file => file.size > this.maxFileSize
    );

    if (oversizedFile) {
      this.errorMessage = (
        'Each image must be 5 MB or smaller.'
      );
      return;
    }

    // Validate total upload size.
    const totalSize = files.reduce(
      (total, file) => total + file.size,
      0
    );

    if (totalSize > this.maxTotalSize) {
      this.errorMessage = (
        'Total upload size exceeds 25 MB.'
      );
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
          this.errorMessage = (
            `Unable to preview ${file.name}.`
          );
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
    this.errorMessage = '';

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

            this.errorMessage = (
              `Analysis failed at stage: ${stage}`
            );

          } else if (error.status === 0) {

            this.errorMessage = (
              'Cannot connect to the backend API. ' +
              'Please check FastAPI and CORS settings.'
            );

          } else {

            this.errorMessage = (
              'Unable to analyze documents. ' +
              'Please try again.'
            );
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
    this.errorMessage = '';
  }
}