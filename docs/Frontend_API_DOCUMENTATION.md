# BuzzFeed UI Clone - Backend API Documentation

This document outlines all the backend APIs required for the BuzzFeed UI Clone frontend to function successfully.

## Base URL
```
https://api.buzzfeed-clone.com/v1
```

## Data Models

### Author
```typescript
interface Author {
  id: string;
  name: string;
  avatar: string;
}
```

### Article
```typescript
interface Article {
  id: string;
  title: string;
  description: string;
  image: string;
  category: string;
  author: Author;
  date: string;
  readTime: string;
  tags: string[];
  isFeatured?: boolean;
  isTrending?: boolean;
}
```

### Quiz
```typescript
interface Quiz {
  id: string;
  title: string;
  description: string;
  image: string;
  category: string;
  questionCount: number;
  author: Author;
  date: string;
}
```

### QuizQuestion
```typescript
interface QuizQuestion {
  id: number;
  question: string;
  options: string[];
}
```

### QuizResult
```typescript
interface QuizResult {
  type: string;
  title: string;
  description: string;
  image?: string;
}
```

### Category
```typescript
interface Category {
  id: string;
  name: string;
  slug: string;
  icon?: string;
}
```

## API Endpoints

### 1. Categories

#### Get All Categories
```http
GET /categories
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "1",
      "name": "Trending",
      "slug": "trending"
    },
    {
      "id": "2", 
      "name": "Entertainment",
      "slug": "entertainment"
    },
    {
      "id": "3",
      "name": "Food", 
      "slug": "food"
    },
    {
      "id": "4",
      "name": "Quiz",
      "slug": "quiz"
    },
    {
      "id": "5",
      "name": "Lifestyle",
      "slug": "lifestyle"
    },
    {
      "id": "6",
      "name": "Travel",
      "slug": "travel"
    },
    {
      "id": "7",
      "name": "Fashion",
      "slug": "fashion"
    },
    {
      "id": "8",
      "name": "Tech",
      "slug": "tech"
    },
    {
      "id": "9",
      "name": "Wellness",
      "slug": "wellness"
    },
    {
      "id": "10",
      "name": "Animals",
      "slug": "animals"
    }
  ]
}
```

### 2. Articles

#### Get All Articles
```http
GET /articles?page=1&limit=20&sort=latest
```

**Query Parameters:**
- `page` (optional): Page number for pagination (default: 1)
- `limit` (optional): Number of articles per page (default: 20)
- `sort` (optional): Sort order - `latest`, `trending`, `popular` (default: `latest`)

**Response:**
```json
{
  "success": true,
  "data": {
    "articles": [
      {
        "id": "1",
        "title": "15 Things That Will Make You Say \"This Is SO Relatable\"",
        "description": "We all have those moments that just hit different. Here are 15 situations that will make you nod your head in agreement.",
        "image": "https://images.unsplash.com/photo-1524019494804-8c1be7b5ba4b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=800",
        "category": "Trending",
        "author": {
          "id": "1",
          "name": "Priya Sharma",
          "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop"
        },
        "date": "2026-03-28",
        "readTime": "4 min read",
        "tags": ["relatable", "trending", "lifestyle"],
        "isFeatured": true,
        "isTrending": true
      }
    ],
    "pagination": {
      "currentPage": 1,
      "totalPages": 5,
      "totalArticles": 100,
      "hasNext": true,
      "hasPrev": false
    }
  }
}
```

#### Get Featured Articles
```http
GET /articles/featured?limit=5
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "1",
      "title": "15 Things That Will Make You Say \"This Is SO Relatable\"",
      "description": "We all have those moments that just hit different. Here are 15 situations that will make you nod your head in agreement.",
      "image": "https://images.unsplash.com/photo-1524019494804-8c1be7b5ba4b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=800",
      "category": "Trending",
      "author": {
        "id": "1",
        "name": "Priya Sharma",
        "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop"
      },
      "date": "2026-03-28",
      "readTime": "4 min read",
      "tags": ["relatable", "trending", "lifestyle"],
      "isFeatured": true,
      "isTrending": true
    }
  ]
}
```

#### Get Trending Articles
```http
GET /articles/trending?limit=10
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "1",
      "title": "15 Things That Will Make You Say \"This Is SO Relatable\"",
      "description": "We all have those moments that just hit different. Here are 15 situations that will make you nod your head in agreement.",
      "image": "https://images.unsplash.com/photo-1524019494804-8c1be7b5ba4b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=800",
      "category": "Trending",
      "author": {
        "id": "1",
        "name": "Priya Sharma",
        "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop"
      },
      "date": "2026-03-28",
      "readTime": "4 min read",
      "tags": ["relatable", "trending", "lifestyle"],
      "isFeatured": true,
      "isTrending": true
    }
  ]
}
```

#### Get Articles by Category
```http
GET /articles/category/{slug}?page=1&limit=20
```

**Path Parameters:**
- `slug`: Category slug (e.g., `trending`, `food`, `entertainment`)

**Query Parameters:**
- `page` (optional): Page number for pagination (default: 1)
- `limit` (optional): Number of articles per page (default: 20)

**Response:**
```json
{
  "success": true,
  "data": {
    "category": {
      "id": "2",
      "name": "Food",
      "slug": "food"
    },
    "articles": [
      {
        "id": "2",
        "title": "23 Delicious Street Food Dishes You Need to Try Right Now",
        "description": "From crispy samosas to spicy pani puri, these street food favorites will make your mouth water.",
        "image": "https://images.unsplash.com/photo-1762898842219-ca8136061b76?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=800",
        "category": "Food",
        "author": {
          "id": "2",
          "name": "Rahul Verma",
          "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop"
        },
        "date": "2026-03-27",
        "readTime": "6 min read",
        "tags": ["food", "street food", "indian cuisine"],
        "isTrending": true
      }
    ],
    "pagination": {
      "currentPage": 1,
      "totalPages": 3,
      "totalArticles": 45,
      "hasNext": true,
      "hasPrev": false
    }
  }
}
```

#### Get Article by ID
```http
GET /articles/{id}
```

**Path Parameters:**
- `id`: Article ID

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "1",
    "title": "15 Things That Will Make You Say \"This Is SO Relatable\"",
    "description": "We all have those moments that just hit different. Here are 15 situations that will make you nod your head in agreement.",
    "image": "https://images.unsplash.com/photo-1524019494804-8c1be7b5ba4b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=800",
    "category": "Trending",
    "author": {
      "id": "1",
      "name": "Priya Sharma",
      "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop"
    },
    "date": "2026-03-28",
    "readTime": "4 min read",
    "tags": ["relatable", "trending", "lifestyle"],
    "isFeatured": true,
    "isTrending": true,
    "content": "Full article content in HTML or Markdown format..."
  }
}
```

#### Get Related Articles
```http
GET /articles/{id}/related?limit=4
```

**Path Parameters:**
- `id`: Article ID

**Query Parameters:**
- `limit` (optional): Number of related articles (default: 4)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "2",
      "title": "23 Delicious Street Food Dishes You Need to Try Right Now",
      "description": "From crispy samosas to spicy pani puri, these street food favorites will make your mouth water.",
      "image": "https://images.unsplash.com/photo-1762898842219-ca8136061b76?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=800",
      "category": "Food",
      "author": {
        "id": "2",
        "name": "Rahul Verma",
        "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop"
      },
      "date": "2026-03-27",
      "readTime": "6 min read",
      "tags": ["food", "street food", "indian cuisine"],
      "isTrending": true
    }
  ]
}
```

### 3. Quizzes

#### Get All Quizzes
```http
GET /quizzes?page=1&limit=20
```

**Query Parameters:**
- `page` (optional): Page number for pagination (default: 1)
- `limit` (optional): Number of quizzes per page (default: 20)

**Response:**
```json
{
  "success": true,
  "data": {
    "quizzes": [
      {
        "id": "q1",
        "title": "Which Bollywood Character Are You?",
        "description": "Answer these questions to find out which iconic Bollywood character matches your personality!",
        "image": "https://images.unsplash.com/photo-1677582774218-0f03f727f47b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=800",
        "category": "Quiz",
        "questionCount": 10,
        "author": {
          "id": "3",
          "name": "Anjali Patel",
          "avatar": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop"
        },
        "date": "2026-03-28"
      }
    ],
    "pagination": {
      "currentPage": 1,
      "totalPages": 2,
      "totalQuizzes": 25,
      "hasNext": true,
      "hasPrev": false
    }
  }
}
```

#### Get Quiz by ID
```http
GET /quizzes/{id}
```

**Path Parameters:**
- `id`: Quiz ID

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "q1",
    "title": "Which Bollywood Character Are You?",
    "description": "Answer these questions to find out which iconic Bollywood character matches your personality!",
    "image": "https://images.unsplash.com/photo-1677582774218-0f03f727f47b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=800",
    "category": "Quiz",
    "questionCount": 10,
    "author": {
      "id": "3",
      "name": "Anjali Patel",
      "avatar": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop"
    },
    "date": "2026-03-28"
  }
}
```

#### Get Quiz Questions
```http
GET /quizzes/{id}/questions
```

**Path Parameters:**
- `id`: Quiz ID

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "question": "What's your go-to weekend activity?",
      "options": [
        "Binge-watching shows",
        "Outdoor adventure", 
        "Cooking a feast",
        "Reading a book"
      ]
    },
    {
      "id": 2,
      "question": "Pick a color that speaks to you:",
      "options": [
        "Vibrant Red",
        "Calm Blue",
        "Sunny Yellow", 
        "Mysterious Purple"
      ]
    }
  ]
}
```

#### Submit Quiz Answers
```http
POST /quizzes/{id}/submit
```

**Path Parameters:**
- `id`: Quiz ID

**Request Body:**
```json
{
  "answers": {
    "1": 0,
    "2": 1,
    "3": 2,
    "4": 1,
    "5": 3
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "result": {
      "type": "The Adventurous Spirit",
      "title": "The Adventurous Spirit",
      "description": "Based on your answers, you're someone who loves new experiences and isn't afraid to step out of your comfort zone!",
      "image": "https://images.unsplash.com/photo-1551698618-1dfe5d97d256?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400"
    },
    "score": {
      "correct": 4,
      "total": 5,
      "percentage": 80
    },
    "recommendations": [
      {
        "id": "q2",
        "title": "Can You Guess The Food From Just One Ingredient?",
        "image": "https://images.unsplash.com/photo-1762898842219-ca8136061b76?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=400"
      }
    ]
  }
}
```

### 4. Search

#### Search Articles and Quizzes
```http
GET /search?q={query}&type=all&page=1&limit=20
```

**Query Parameters:**
- `q`: Search query
- `type` (optional): Content type - `all`, `articles`, `quizzes` (default: `all`)
- `page` (optional): Page number for pagination (default: 1)
- `limit` (optional): Number of results per page (default: 20)

**Response:**
```json
{
  "success": true,
  "data": {
    "query": "food",
    "results": {
      "articles": [
        {
          "id": "2",
          "title": "23 Delicious Street Food Dishes You Need to Try Right Now",
          "description": "From crispy samosas to spicy pani puri, these street food favorites will make your mouth water.",
          "image": "https://images.unsplash.com/photo-1762898842219-ca8136061b76?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=800",
          "category": "Food",
          "author": {
            "id": "2",
            "name": "Rahul Verma",
            "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop"
          },
          "date": "2026-03-27",
          "readTime": "6 min read",
          "tags": ["food", "street food", "indian cuisine"],
          "isTrending": true
        }
      ],
      "quizzes": [
        {
          "id": "q2",
          "title": "Can You Guess The Food From Just One Ingredient?",
          "description": "Test your culinary knowledge with this challenging food quiz!",
          "image": "https://images.unsplash.com/photo-1762898842219-ca8136061b76?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=800",
          "category": "Quiz",
          "questionCount": 15,
          "author": {
            "id": "3",
            "name": "Anjali Patel",
            "avatar": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop"
          },
          "date": "2026-03-27"
        }
      ]
    },
    "pagination": {
      "currentPage": 1,
      "totalPages": 3,
      "totalResults": 45,
      "hasNext": true,
      "hasPrev": false
    }
  }
}
```

### 5. Authors

#### Get Author by ID
```http
GET /authors/{id}
```

**Path Parameters:**
- `id`: Author ID

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "1",
    "name": "Priya Sharma",
    "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop",
    "bio": "Passionate writer about lifestyle and trending topics.",
    "articleCount": 25,
    "quizCount": 5,
    "socialLinks": {
      "twitter": "@priyasharma",
      "instagram": "@priya.writes"
    }
  }
}
```

#### Get Author's Articles
```http
GET /authors/{id}/articles?page=1&limit=20
```

**Path Parameters:**
- `id`: Author ID

**Query Parameters:**
- `page` (optional): Page number for pagination (default: 1)
- `limit` (optional): Number of articles per page (default: 20)

**Response:**
```json
{
  "success": true,
  "data": {
    "author": {
      "id": "1",
      "name": "Priya Sharma",
      "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop"
    },
    "articles": [
      {
        "id": "1",
        "title": "15 Things That Will Make You Say \"This Is SO Relatable\"",
        "description": "We all have those moments that just hit different. Here are 15 situations that will make you nod your head in agreement.",
        "image": "https://images.unsplash.com/photo-1524019494804-8c1be7b5ba4b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=800",
        "category": "Trending",
        "date": "2026-03-28",
        "readTime": "4 min read",
        "tags": ["relatable", "trending", "lifestyle"],
        "isFeatured": true,
        "isTrending": true
      }
    ],
    "pagination": {
      "currentPage": 1,
      "totalPages": 2,
      "totalArticles": 25,
      "hasNext": true,
      "hasPrev": false
    }
  }
}
```

### 6. Analytics (Optional)

#### Track Article View
```http
POST /analytics/article-view
```

**Request Body:**
```json
{
  "articleId": "1",
  "userId": null,
  "timestamp": "2026-03-28T10:30:00Z",
  "source": "direct",
  "userAgent": "Mozilla/5.0..."
}
```

#### Track Quiz Completion
```http
POST /analytics/quiz-completion
```

**Request Body:**
```json
{
  "quizId": "q1",
  "userId": null,
  "result": "The Adventurous Spirit",
  "score": 80,
  "timeSpent": 300,
  "timestamp": "2026-03-28T10:30:00Z"
}
```

## Error Responses

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Article not found",
    "details": "Article with ID 'invalid-id' does not exist"
  }
}
```

### Common Error Codes:
- `NOT_FOUND`: Resource not found
- `VALIDATION_ERROR`: Invalid request parameters
- `INTERNAL_ERROR`: Server error
- `UNAUTHORIZED`: Authentication required
- `RATE_LIMIT_EXCEEDED`: Too many requests

## Rate Limiting

- **Public endpoints**: 100 requests per minute per IP
- **Search endpoints**: 30 requests per minute per IP
- **Analytics endpoints**: 1000 requests per minute per IP

## Caching

- **Articles**: 5 minutes cache
- **Categories**: 1 hour cache  
- **Trending content**: 10 minutes cache
- **Quiz questions**: 30 minutes cache

## Authentication (Future Enhancement)

While the current frontend doesn't require authentication, future features may include:

- User profiles
- Saved articles
- Quiz history
- Comments
- Likes/shares

When implemented, use JWT tokens with `Authorization: Bearer {token}` header.

## Sample Implementation Notes

1. **Images**: All image URLs should support CDN optimization
2. **Dates**: Use ISO 8601 format (YYYY-MM-DD)
3. **Pagination**: Use zero-based page indexing
4. **Search**: Implement fuzzy search with relevance scoring
5. **Trending Algorithm**: Based on views, shares, and recency
6. **Related Content**: Use category matching and tag similarity

## Testing

Use these sample IDs for testing:
- Articles: `1`, `2`, `3`, `4`, `5`
- Quizzes: `q1`, `q2`, `q3`, `q4`
- Authors: `1`, `2`, `3`, `4`, `5`
- Categories: `trending`, `food`, `entertainment`, `quiz`, `lifestyle`
