import ReactMarkdown from 'react-markdown';
import './CodeReview.css';

export default function CodeReview({ reviews }) {
  if (!reviews || reviews.length === 0) {
    return null;
  }

  return (
    <div className="code-review">
      <h3 className="code-review-title">Code Reviews</h3>
      <div className="code-review-list">
        {reviews.map((review, index) => (
          <ReviewCard
            key={index}
            review={review}
          />
        ))}
      </div>
    </div>
  );
}

function ReviewCard({ review }) {
  const parsed = review.parsed_review || {};
  const submissions = parsed.submissions || {};
  const ranking = parsed.ranking || [];

  return (
    <div className="review-card">
      <div className="review-card-header">
        <span className="review-reviewer">
          Reviewer: {review.model.split('/')[1] || review.model}
        </span>
        {review.node && (
          <span className="review-node">Node: {review.node}</span>
        )}
      </div>

      {Object.keys(submissions).length > 0 && (
        <div className="review-submissions">
          {Object.entries(submissions).map(([label, submission]) => (
            <div key={label} className="review-submission">
              <div className="review-submission-header">
                <span className="review-label">Code Submission {label}</span>
                {submission.score !== null && submission.score !== undefined && (
                  <span className="review-score">
                    Score: {submission.score}/10
                  </span>
                )}
              </div>

              <div className="review-categories">
                {submission.categories && Object.entries(submission.categories).map(([category, feedback]) => (
                  <div key={category} className="review-category">
                    <div className="review-category-header">
                      <span className="review-category-icon">
                        {getCategoryIcon(category)}
                      </span>
                      <span className="review-category-name">
                        {formatCategoryName(category)}
                      </span>
                    </div>
                    <div className="review-category-content">
                      <ReactMarkdown>{feedback}</ReactMarkdown>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {ranking.length > 0 && (
        <div className="review-ranking">
          <h4 className="review-ranking-title">Ranking</h4>
          <ol className="review-ranking-list">
            {ranking.map((label, idx) => (
              <li key={idx}>
                Code Submission {label}
              </li>
            ))}
          </ol>
        </div>
      )}

      {review.review_text && (
        <details className="review-full-text">
          <summary>Full Review Text</summary>
          <div className="review-full-content">
            <ReactMarkdown>{review.review_text}</ReactMarkdown>
          </div>
        </details>
      )}
    </div>
  );
}

function getCategoryIcon(category) {
  const icons = {
    bugs: '🐛',
    style: '🎨',
    performance: '⚡',
    security: '🔒',
    'best practices': '✨',
  };
  return icons[category.toLowerCase()] || '📝';
}

function formatCategoryName(category) {
  const names = {
    bugs: 'Bugs & Issues',
    style: 'Code Style',
    performance: 'Performance',
    security: 'Security',
    'best practices': 'Best Practices',
  };
  return names[category.toLowerCase()] || category;
}

