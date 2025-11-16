/**
 * Global type declarations for React Native
 */

declare var __DEV__: boolean;

// React Native global types
declare module 'react-native-keychain' {
  export interface UserCredentials {
    username: string;
    password: string;
  }

  export function setInternetCredentials(
    server: string,
    username: string,
    password: string
  ): Promise<boolean>;

  export function getInternetCredentials(
    server: string
  ): Promise<false | UserCredentials>;

  export function resetInternetCredentials(server: string): Promise<boolean>;
}

declare module 'react-native-toast-message' {
  interface ToastConfig {
    type: 'success' | 'error' | 'info';
    text1?: string;
    text2?: string;
    visibilityTime?: number;
  }

  export default class Toast {
    static show(config: ToastConfig): void;
    static hide(): void;
  }
}

declare module 'react-native-document-picker' {
  export interface DocumentPickerResponse {
    uri: string;
    type: string;
    name: string;
    size: number;
  }

  export interface DocumentPickerOptions {
    type?: string[];
    allowMultiSelection?: boolean;
  }

  export function pick(options?: DocumentPickerOptions): Promise<DocumentPickerResponse[]>;
  export function pickSingle(options?: DocumentPickerOptions): Promise<DocumentPickerResponse>;
}

declare module 'react-native-image-picker' {
  export interface ImagePickerResponse {
    uri?: string;
    type?: string;
    fileName?: string;
    fileSize?: number;
  }

  export interface ImagePickerOptions {
    mediaType?: 'photo' | 'video' | 'mixed';
    includeBase64?: boolean;
    maxHeight?: number;
    maxWidth?: number;
    quality?: number;
  }

  export function launchImageLibrary(
    options: ImagePickerOptions,
    callback: (response: ImagePickerResponse) => void
  ): void;

  export function launchCamera(
    options: ImagePickerOptions,
    callback: (response: ImagePickerResponse) => void
  ): void;
}

declare module 'react-native-file-viewer' {
  export function open(filePath: string, options?: any): Promise<void>;
}

declare module 'react-native-fs' {
  export const DocumentDirectoryPath: string;
  export const DownloadDirectoryPath: string;

  export function downloadFile(options: {
    fromUrl: string;
    toFile: string;
    headers?: Record<string, string>;
  }): { promise: Promise<any> };

  export function exists(filePath: string): Promise<boolean>;
  export function writeFile(filePath: string, contents: string, encoding?: string): Promise<void>;
  export function readFile(filePath: string, encoding?: string): Promise<string>;
}
