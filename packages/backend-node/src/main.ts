import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { assertDatabaseModeBoundary, getAppMode } from './runtime-mode';
// import { TransformInterceptor } from './common/interceptors/transform.interceptor';
// import { HttpExceptionFilter } from './common/filters/http-exception.filter';

async function bootstrap() {
  const appMode = getAppMode();
  assertDatabaseModeBoundary();
  const port = process.env.PORT ?? 4000;
  const app = await NestFactory.create(AppModule);
  // app.useGlobalFilters(new HttpExceptionFilter());
  // app.useGlobalInterceptors(new TransformInterceptor());
  app.setGlobalPrefix('api');
  app.enableCors();
  await app.listen(port);
  console.log(
    `Backend is running in ${appMode} mode on: http://localhost:${port}`,
  );
}
void bootstrap();
