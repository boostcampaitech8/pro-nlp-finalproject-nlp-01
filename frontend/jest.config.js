/* eslint-disable @typescript-eslint/no-require-imports */
const nextJest = require('next/jest');

const createJestConfig = nextJest({
    dir: './',
});

const config = {
    coverageProvider: 'v8',
    testEnvironment: 'jest-environment-jsdom',
    setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
    moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/src/$1',
    },
    testEnvironmentOptions: {
        customExportConditions: [''],
    },
};

module.exports = async () => {
    const jestConfig = await createJestConfig(config)();
    jestConfig.transformIgnorePatterns = [
        '/node_modules/(?!(msw|@mswjs|undici|until-async)/)',
        '^.+\\.module\\.(css|sass|scss)$',
    ];
    return jestConfig;
};
