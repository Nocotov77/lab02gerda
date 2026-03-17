const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');
const { 
  validateCreateTask, 
  validateUpdateTask, 
  validateId 
} = require('../middleware/validation');
const { 
  initializeDataFile, 
  readData, 
  writeData, 
  getNextId 
} = require('../utils/fileOperations');

// Инициализация файла данных при запуске
initializeDataFile();

// GET /api/tasks - получение всех задач с фильтрацией, сортировкой и пагинацией
router.get('/', async (req, res, next) => {
  try {
    const { category, completed, priority, sortBy, page = 1, limit = 10 } = req.query;
    const data = await readData();
    let tasks = [...data.tasks];

    // Фильтрация по категории
    if (category) {
      tasks = tasks.filter(task => task.category === category);
    }

    // Фильтрация по статусу выполнения
    if (completed !== undefined) {
      const isCompleted = completed === 'true';
      tasks = tasks.filter(task => task.completed === isCompleted);
    }

    // Фильтрация по приоритету (можно передать несколько через запятую)
    if (priority) {
      const priorities = priority.split(',').map(Number);
      tasks = tasks.filter(task => priorities.includes(task.priority));
    }

    // Сортировка
    if (sortBy) {
      const [field, order] = sortBy.startsWith('-') 
        ? [sortBy.substring(1), 'desc'] 
        : [sortBy, 'asc'];
      
      tasks.sort((a, b) => {
        if (field === 'dueDate' || field === 'createdAt') {
          const dateA = new Date(a[field] || 0);
          const dateB = new Date(b[field] || 0);
          return order === 'asc' ? dateA - dateB : dateB - dateA;
        } else if (field === 'priority') {
          return order === 'asc' ? a.priority - b.priority : b.priority - a.priority;
        }
        return 0;
      });
    }

    // Пагинация
    const startIndex = (page - 1) * limit;
    const endIndex = page * limit;
    const paginatedTasks = tasks.slice(startIndex, endIndex);

    res.json({
      success: true,
      count: paginatedTasks.length,
      total: tasks.length,
      page: parseInt(page),
      limit: parseInt(limit),
      data: paginatedTasks
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/tasks/:id - получение задачи по ID
router.get('/:id', validateId, async (req, res, next) => {
  try {
    const taskId = req.params.id;
    const data = await readData();
    const task = data.tasks.find(t => t.id === taskId);

    if (!task) {
      return res.status(404).json({
        success: false,
        error: 'Задача не найдена'
      });
    }

    res.json({
      success: true,
      data: task
    });
  } catch (error) {
    next(error);
  }
});

// POST /api/tasks - создание новой задачи
router.post('/', validateCreateTask, async (req, res, next) => {
  try {
    const { title, description, category, priority, dueDate } = req.body;
    const data = await readData();

    const newTask = {
      id: await getNextId(),
      uuid: uuidv4(),
      title,
      description: description || '',
      category: category || 'personal',
      priority: priority || 3,
      dueDate: dueDate || null,
      completed: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    data.tasks.push(newTask);
    await writeData(data);

    res.status(201).json({
      success: true,
      message: 'Задача успешно создана',
      data: newTask
    });
  } catch (error) {
    next(error);
  }
});

// PUT /api/tasks/:id - полное обновление задачи (частичное для удобства)
router.put('/:id', validateId, validateUpdateTask, async (req, res, next) => {
  try {
    const taskId = req.params.id;
    const updates = req.body;
    const data = await readData();

    const taskIndex = data.tasks.findIndex(t => t.id === taskId);
    if (taskIndex === -1) {
      return res.status(404).json({
        success: false,
        error: 'Задача не найдена'
      });
    }

    const updatedTask = {
      ...data.tasks[taskIndex],
      ...updates,
      updatedAt: new Date().toISOString()
    };

    data.tasks[taskIndex] = updatedTask;
    await writeData(data);

    res.json({
      success: true,
      message: 'Задача успешно обновлена',
      data: updatedTask
    });
  } catch (error) {
    next(error);
  }
});

// PATCH /api/tasks/:id/complete - отметка задачи как выполненной
router.patch('/:id/complete', validateId, async (req, res, next) => {
  try {
    const taskId = req.params.id;
    const data = await readData();

    const task = data.tasks.find(t => t.id === taskId);
    if (!task) {
      return res.status(404).json({
        success: false,
        error: 'Задача не найдена'
      });
    }

    task.completed = true;
    task.updatedAt = new Date().toISOString();
    await writeData(data);

    res.json({
      success: true,
      message: 'Задача отмечена как выполненная',
      data: task
    });
  } catch (error) {
    next(error);
  }
});

// DELETE /api/tasks/:id - удаление задачи
router.delete('/:id', validateId, async (req, res, next) => {
  try {
    const taskId = req.params.id;
    const data = await readData();

    const taskIndex = data.tasks.findIndex(t => t.id === taskId);
    if (taskIndex === -1) {
      return res.status(404).json({
        success: false,
        error: 'Задача не найдена'
      });
    }

    data.tasks.splice(taskIndex, 1);
    await writeData(data);

    res.json({
      success: true,
      message: 'Задача успешно удалена'
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/tasks/stats/summary - статистика по задачам
router.get('/stats/summary', async (req, res, next) => {
  try {
    const data = await readData();
    const tasks = data.tasks;
    const now = new Date();

    const stats = {
      total: tasks.length,
      completed: 0,
      pending: 0,
      overdue: 0,
      byCategory: {},
      byPriority: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 }
    };

    tasks.forEach(task => {
      // По статусу
      if (task.completed) {
        stats.completed++;
      } else {
        stats.pending++;
      }

      // Просроченные (не выполнены и dueDate в прошлом)
      if (!task.completed && task.dueDate) {
        const due = new Date(task.dueDate);
        if (due < now) {
          stats.overdue++;
        }
      }

      // По категориям
      const cat = task.category;
      stats.byCategory[cat] = (stats.byCategory[cat] || 0) + 1;

      // По приоритетам
      const prio = task.priority;
      if (prio >= 1 && prio <= 5) {
        stats.byPriority[prio]++;
      }
    });

    res.json({
      success: true,
      data: stats
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/tasks/search/text - поиск задач по тексту
router.get('/search/text', async (req, res, next) => {
  try {
    const { q } = req.query;

    if (!q || q.trim().length < 2) {
      return res.status(400).json({
        success: false,
        error: 'Поисковый запрос должен содержать минимум 2 символа'
      });
    }

    const data = await readData();
    const searchTerm = q.toLowerCase().trim();

    const results = data.tasks.filter(task => {
      const titleMatch = task.title.toLowerCase().includes(searchTerm);
      const descMatch = task.description.toLowerCase().includes(searchTerm);
      return titleMatch || descMatch;
    });

    res.json({
      success: true,
      count: results.length,
      data: results
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;