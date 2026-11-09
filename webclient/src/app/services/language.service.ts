
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject } from 'rxjs';

export type UiLanguage = 'en' | 'ja';

@Injectable({
  providedIn: 'root'
})
export class LanguageService {
  private readonly storageKey = 'clinplain.uiLanguage';

  private readonly dictionaries: Record<
    UiLanguage,
    Record<string, string>
  > = {
    en: {},
    ja: {}
  };

  private readonly languageSubject =
    new BehaviorSubject<UiLanguage>(this.getSavedLanguage());

  readonly language$ = this.languageSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadTranslations('en');
    this.loadTranslations('ja');
  }

  get currentLanguage(): UiLanguage {
    return this.languageSubject.value;
  }

  setLanguage(language: UiLanguage): void {
    if (language !== 'en' && language !== 'ja') {
      return;
    }

    this.languageSubject.next(language);

    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(this.storageKey, language);
    }
  }

  translate(key: string): string {
    return (
      this.dictionaries[this.currentLanguage][key] ??
      this.dictionaries.en[key] ??
      key
    );
  }

  private loadTranslations(language: UiLanguage): void {
    this.http
      .get<Record<string, string>>(
        `assets/i18n/${language}.json`
      )
      .subscribe({
        next: (translations) => {
          this.dictionaries[language] = translations;

          // Notify Angular that translations are ready.
          this.languageSubject.next(this.currentLanguage);
        },
        error: (error) => {
          console.error(
            `Failed to load ${language} translations:`,
            error
          );
        }
      });
  }

  private getSavedLanguage(): UiLanguage {
    if (typeof localStorage === 'undefined') {
      return 'en';
    }

    return localStorage.getItem(this.storageKey) === 'ja'
      ? 'ja'
      : 'en';
  }
}
