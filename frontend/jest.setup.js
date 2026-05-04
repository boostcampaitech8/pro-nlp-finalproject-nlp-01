/* eslint-disable @typescript-eslint/no-require-imports */
require('@testing-library/jest-dom');

// Next.js/MSW/Node 환경에서 필요한 폴리필을 최상단에서 정의
const { TextEncoder, TextDecoder } = require('util');
const { MessageChannel, MessagePort, BroadcastChannel } = require('worker_threads');

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
global.MessageChannel = MessageChannel;
global.MessagePort = MessagePort;
global.BroadcastChannel = BroadcastChannel;

if (!global.ReadableStream) {
    const { ReadableStream, TransformStream, WritableStream } = require('stream/web');
    global.ReadableStream = ReadableStream;
    global.TransformStream = TransformStream;
    global.WritableStream = WritableStream;
}

// Blob & File polyfills (undici can provide these, or check global)
if (!global.Blob) {
    const { Blob, File } = require('undici');
    global.Blob = Blob;
    global.File = File;
}

// fetch API 폴리필 (Node 20 및 JSDOM 환경 대응)
const { fetch, Request, Response, Headers } = require('undici');
global.fetch = fetch;
global.Request = Request;
global.Response = Response;
global.Headers = Headers;

const { server } = require('./src/mocks/server');

// Radix UI 등을 위한 추가 폴리필
global.ResizeObserver = jest.fn().mockImplementation(() => ({
    observe: jest.fn(),
    unobserve: jest.fn(),
    disconnect: jest.fn(),
}));

global.IntersectionObserver = jest.fn().mockImplementation(() => ({
    observe: jest.fn(),
    unobserve: jest.fn(),
    disconnect: jest.fn(),
}));

// MSW 서버 설정
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
