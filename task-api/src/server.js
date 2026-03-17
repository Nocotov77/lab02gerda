require('dotenv').config();
const app = require('./app');

const PORT = process.env.PORT || 3000;

// Запуск сервера
app.listen(PORT, () => {
  console.log(`🚀 Сервер запущен на порту ${PORT}`);
  console.log(`📚 Документация API доступна по адресу: http://localhost:${PORT}/api/tasks`);
  console.log(`🌐 Режим: ${process.env.NODE_ENV || 'development'}`);
});

// Обработка неожиданных ошибок
process.on('unhandledRejection', (err) => {
  console.error('Unhandled Rejection:', err);
  // В продакшене можно завершить процесс
  // process.exit(1);
});

process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception:', err);
  // В продакшене можно завершить процесс
  // process.exit(1);
});