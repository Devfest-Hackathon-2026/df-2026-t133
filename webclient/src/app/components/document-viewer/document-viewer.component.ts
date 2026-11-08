import {
  Component,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges
} from '@angular/core';

import {
  OCRPage,
  OCRSource,
  OCRPoint
} from '../../app.service';


interface DocumentPreview {
  name: string;
  url: string;
  error: boolean;
}

interface HighlightStyle {
  left: string;
  top: string;
  width: string;
  height: string;
}


@Component({
  selector: 'app-document-viewer',
  templateUrl: './document-viewer.component.html',
  styleUrls: ['./document-viewer.component.scss']
})
export class DocumentViewerComponent
  implements OnChanges, OnDestroy {

  @Input() files: File[] = [];
  @Input() ocrPages: OCRPage[] = [];
  @Input() selectedSource: OCRSource | null = null;

  previews: DocumentPreview[] = [];

  activePageIndex = 0;

  highlightStyle: HighlightStyle | null = null;

  private loadVersion = 0;

  /**
   * Handle changes from AppComponent.
   */
  ngOnChanges(changes: SimpleChanges): void {

    if (changes['files']) {
      this.loadPreviews();
    }

    if (changes['selectedSource'] && this.selectedSource) {
      const index = this.selectedSource.page_index;

      if (index >= 0 && index < this.files.length) {
        this.activePageIndex = index;
      }
    }

    if (
      changes['files'] ||
      changes['ocrPages'] ||
      changes['selectedSource']
    ) {
      this.updateHighlight();
    }
  }

  /**
   * Load uploaded images as data URLs.
   */
  private loadPreviews(): void {

    const version = ++this.loadVersion;

    this.activePageIndex = 0;

    this.previews = this.files.map(file => ({
      name: file.name,
      url: '',
      error: false
    }));

    this.files.forEach((file, index) => {

      const reader = new FileReader();

      reader.onload = () => {

        if (version !== this.loadVersion) {
          return;
        }

        const preview = this.previews[index];

        if (preview && typeof reader.result === 'string') {
          preview.url = reader.result;
        }
      };

      reader.onerror = () => {

        if (version !== this.loadVersion) {
          return;
        }

        const preview = this.previews[index];

        if (preview) {
          preview.error = true;
        }
      };

      reader.readAsDataURL(file);
    });
  }

  /**
   * Return the currently displayed image.
   */
  get activePreview(): DocumentPreview | null {
    return this.previews[this.activePageIndex] || null;
  }

  /**
   * Navigate to a page.
   */
  goToPage(index: number): void {

    if (index < 0 || index >= this.previews.length) {
      return;
    }

    this.activePageIndex = index;

    this.updateHighlight();
  }

  previousPage(): void {
    this.goToPage(this.activePageIndex - 1);
  }

  nextPage(): void {
    this.goToPage(this.activePageIndex + 1);
  }

  /**
   * Convert normalized OCR coordinates into CSS
   * percentages for positioning the highlighted region.
   */
  private updateHighlight(): void {

    this.highlightStyle = null;

    const source = this.selectedSource;

    if (!source || source.page_index !== this.activePageIndex) {
      return;
    }

    const page = this.ocrPages.find(
      item => item.page_index === source.page_index
    );

    if (!page) {
      return;
    }

    const line = page.lines[source.source_line_index];

    if (!line || !line.bounding_box || line.bounding_box.length === 0) {
      return;
    }

    // Do not highlight an unrelated OCR line.
    if (line.text.trim() !== source.source_quote.trim()) {
      return;
    }

    const points: OCRPoint[] = line.bounding_box.filter(
      point =>
        Number.isFinite(point.x) &&
        Number.isFinite(point.y)
    );

    if (points.length < 2) {
      return;
    }

    const xs = points.map(point => point.x);
    const ys = points.map(point => point.y);

    const padding = 0.004;

    const left = Math.max(
      0,
      Math.min(...xs) - padding
    );

    const top = Math.max(
      0,
      Math.min(...ys) - padding
    );

    const right = Math.min(
      1,
      Math.max(...xs) + padding
    );

    const bottom = Math.min(
      1,
      Math.max(...ys) + padding
    );

    if (right <= left || bottom <= top) {
      return;
    }

    this.highlightStyle = {
      left: `${left * 100}%`,
      top: `${top * 100}%`,
      width: `${(right - left) * 100}%`,
      height: `${(bottom - top) * 100}%`
    };
  }

  ngOnDestroy(): void {
    // Ignore unfinished FileReader callbacks.
    this.loadVersion++;
  }
}