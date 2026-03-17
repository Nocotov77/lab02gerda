const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const tasksRouter = require('./routes/tasks');
const { notFoundHandler, errorHandler } = require('./middleware/errorHandler');

const app = express();

// Безопасность
app.use(helmet());

// CORS
app.use(cors({
  origin: process.env.CORS_ORIGIN || '*',
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 минут
  max: 100, // максимум 100 запросов с одного IP
  message: {
    error: 'Слишком много запросов. Попробуйте позже.'
  }
});
app.use('/api/', limiter);

// Парсинг JSON
app.use(express.json());

// Логирование запросов (простое)
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.url}`);
  next();
});

// Корневой маршрут
app.get('/', (req, res) => {
  res.json({
    name: 'Task Manager API',
    version: '1.0.0',
    description: 'REST API для управления задачами',
    endpoints: {
      tasks: '/api/tasks',
      stats: '/api/tasks/stats/summary',
      search: '/api/tasks/search/text',
      health: '/health'
    },
    documentation: 'Используйте GET, POST, PUT, PATCH, DELETE запросы для работы с задачами.'
  });
});

// Маршрут для проверки здоровья
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// Routes
app.use('/api/tasks', tasksRouter);

// Обработка 404
app.use(notFoundHandler);

// Обработка ошибок
app.use(errorHandler);

module.exports = app;