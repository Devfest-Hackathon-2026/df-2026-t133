// This file can be replaced during build by using the `fileReplacements` array.
// `ng build` replaces `environment.ts` with `environment.prod.ts`.
// The list of file replacements can be found in `angular.json`.

export const environment = {
  production: false,

  apiUrl: 'http://localhost:8000',

  firebaseConfig: {
    apiKey: 'AIzaSyBcf_cNDJn1BpPt_tF_3hh5l09aFc6jVK8',
    authDomain: 'clinplain-devfest-2026.firebaseapp.com',
    projectId: 'clinplain-devfest-2026',
    storageBucket: 'clinplain-devfest-2026.firebasestorage.app',
    messagingSenderId: '123313351627',
    appId: '1:123313351627:web:d6e044033bfe1d7338244e'
  },

  recaptchaEnterpriseSiteKey:
    '6LfcQRYuAAAAAGjFJR0cvsULdCutn-tQRscqu12E'
};

/*
 * For easier debugging in development mode, you can import the following file
 * to ignore zone related error stack frames such as `zone.run`, `zoneDelegate.invokeTask`.
 *
 * This import should be commented out in production mode because it will have a negative impact
 * on performance if an error is thrown.
 */
// import 'zone.js/plugins/zone-error';  // Included with Angular CLI.
