import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { DocumentUploadComponent } from './components/document-upload/document-upload.component';
import { AnalysisResultsComponent } from './components/analysis-results/analysis-results.component';
import { DocumentViewerComponent } from './components/document-viewer/document-viewer.component';
import { TeachbackComponent } from './components/teachback/teachback.component';

@NgModule({
  declarations: [
    AppComponent,
    DocumentUploadComponent,
    AnalysisResultsComponent,
    DocumentViewerComponent,
    TeachbackComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule
  ],
  providers: [],
  bootstrap: [
    AppComponent
  ]
})
export class AppModule {}