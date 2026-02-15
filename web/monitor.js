/**
 * JTF News Operations Dashboard
 * Polls monitor.json every 10 seconds and updates the UI
 */

const POLL_INTERVAL = 10000; // 10 seconds
const STALE_THRESHOLD = 600000; // 10 minutes in ms
const MONITOR_URL = '../data/monitor.json';

let lastFetchTime = null;
let pollTimer = null;

/**
 * Format seconds into human-readable uptime string
 */
function formatUptime(seconds) {
    if (!seconds || seconds < 0) return '--';

    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) {
        return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else {
        return `${minutes}m`;
    }
}

/**
 * Format hours into human-readable string
 */
function formatHours(hours) {
    if (!hours || hours < 0) return '--';

    if (hours < 1) {
        return `${Math.round(hours * 60)}m`;
    } else if (hours < 24) {
        return `${hours.toFixed(1)}h`;
    } else {
        return `${Math.floor(hours / 24)}d ${Math.round(hours % 24)}h`;
    }
}

/**
 * Format currency
 */
function formatCurrency(amount) {
    if (typeof amount !== 'number') return '$0.00';
    return '$' + amount.toFixed(2);
}

/**
 * Format timestamp for display
 */
function formatTimestamp(isoString) {
    if (!isoString) return '--';

    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;

    // If less than a minute ago
    if (diff < 60000) {
        return 'Just now';
    }

    // If less than an hour ago
    if (diff < 3600000) {
        const mins = Math.floor(diff / 60000);
        return `${mins}m ago`;
    }

    // If today
    if (date.toDateString() === now.toDateString()) {
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Format error timestamp
 */
function formatErrorTime(isoString) {
    if (!isoString) return '';

    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus(status) {
    const badge = document.getElementById('connection-status');
    badge.className = 'status-badge';

    switch (status) {
        case 'connected':
            badge.textContent = 'Connected';
            badge.classList.add('status-ok');
            break;
        case 'error':
            badge.textContent = 'Connection Error';
            badge.classList.add('status-error');
            break;
        case 'stale':
            badge.textContent = 'Stale Data';
            badge.classList.add('status-warning');
            break;
        default:
            badge.textContent = 'Connecting...';
            badge.classList.add('status-unknown');
    }
}

/**
 * Update the dashboard with monitor data
 */
function updateDashboard(data) {
    // Check if data is stale
    const dataTime = new Date(data.timestamp);
    const now = new Date();
    const isStale = (now - dataTime) > STALE_THRESHOLD;

    if (isStale) {
        updateConnectionStatus('stale');
        document.querySelector('.dashboard').classList.add('stale');
    } else {
        updateConnectionStatus('connected');
        document.querySelector('.dashboard').classList.remove('stale');
    }

    // Update last update time
    document.getElementById('last-update').textContent =
        `Updated: ${formatTimestamp(data.timestamp)}`;

    // System Status
    const systemState = document.getElementById('system-state');
    systemState.textContent = data.status?.state || 'Unknown';
    systemState.className = 'status-badge status-' + (data.status?.state || 'unknown');

    document.getElementById('uptime').textContent = formatUptime(data.uptime_seconds);

    // Show monthly availability % if available
    const availabilityEl = document.getElementById('availability');
    if (availabilityEl && data.availability_pct !== undefined) {
        availabilityEl.textContent = `${data.availability_pct}%`;
    }

    const streamHealth = data.status?.stream_health || 'unknown';
    const streamEl = document.getElementById('stream-health');
    streamEl.textContent = streamHealth.charAt(0).toUpperCase() + streamHealth.slice(1);
    streamEl.className = 'stat-value status-' + streamHealth;

    document.getElementById('next-cycle').textContent =
        `${data.status?.next_cycle_minutes || '--'} min`;

    document.getElementById('stories-today').textContent = data.stories_today || 0;

    // API Costs
    const costs = data.api_costs || {};
    const services = costs.today || {};

    document.getElementById('total-cost').textContent = formatCurrency(costs.total_usd);

    // Claude
    const claude = services.claude || {};
    document.getElementById('claude-calls').textContent = `${claude.calls || 0} calls`;
    document.getElementById('claude-cost').textContent = formatCurrency(claude.cost_usd);

    // ElevenLabs
    const elevenlabs = services.elevenlabs || {};
    document.getElementById('elevenlabs-calls').textContent = `${elevenlabs.calls || 0} calls`;
    document.getElementById('elevenlabs-cost').textContent = formatCurrency(elevenlabs.cost_usd);

    // Twilio
    const twilio = services.twilio || {};
    document.getElementById('twilio-calls').textContent = `${twilio.calls || 0} SMS`;
    document.getElementById('twilio-cost').textContent = formatCurrency(twilio.cost_usd);

    // Monthly estimate
    document.getElementById('month-estimate').textContent =
        formatCurrency(costs.month_estimate_usd);

    // Daily budget (dynamic based on days in month)
    const dailyBudgetEl = document.getElementById('daily-budget');
    if (dailyBudgetEl) {
        dailyBudgetEl.textContent = formatCurrency(costs.daily_budget);
    }

    // Current Cycle
    const cycle = data.cycle || {};
    document.getElementById('cycle-number').textContent = `#${cycle.number || 0}`;
    document.getElementById('headlines-scraped').textContent = cycle.headlines_scraped || 0;
    document.getElementById('headlines-processed').textContent = cycle.headlines_processed || 0;
    document.getElementById('stories-published').textContent = cycle.stories_published || 0;
    document.getElementById('stories-queued').textContent = cycle.stories_queued || 0;
    document.getElementById('cycle-duration').textContent =
        cycle.duration_seconds ? `${cycle.duration_seconds}s` : '--';

    // Queue Status
    const queue = data.queue || {};
    document.getElementById('queue-size').textContent = queue.size || 0;
    document.getElementById('oldest-item').textContent =
        queue.oldest_item_age_hours ? formatHours(queue.oldest_item_age_hours) : '--';

    // Source Health
    const sources = data.sources || {};
    const sourcesOk = sources.successful || 0;
    const sourcesTotal = sources.total || 0;
    const failedSources = sources.failed || [];

    document.getElementById('sources-ok').textContent = sourcesOk;
    document.getElementById('sources-total').textContent = sourcesTotal;

    const sourcesStatus = document.getElementById('sources-status');
    if (failedSources.length === 0) {
        sourcesStatus.textContent = 'All OK';
        sourcesStatus.className = 'status-badge status-ok';
    } else if (failedSources.length < sourcesTotal * 0.25) {
        sourcesStatus.textContent = 'Minor Issues';
        sourcesStatus.className = 'status-badge status-warning';
    } else {
        sourcesStatus.textContent = 'Degraded';
        sourcesStatus.className = 'status-badge status-error';
    }

    const failedContainer = document.getElementById('failed-sources');
    if (failedSources.length > 0) {
        failedContainer.innerHTML = failedSources.map(source =>
            `<div class="failed-source">${source}</div>`
        ).join('');
    } else {
        failedContainer.innerHTML = '';
    }

    // Recent Errors
    const errors = data.recent_errors || [];
    const errorCount = document.getElementById('error-count');
    errorCount.textContent = errors.length;

    const errorList = document.getElementById('error-list');
    if (errors.length > 0) {
        errorList.innerHTML = errors.reverse().map(error => {
            const levelClass = error.level === 'WARNING' ? 'warning' : '';
            return `
                <div class="error-item ${levelClass}">
                    <div class="error-time">${formatErrorTime(error.timestamp)}</div>
                    <span class="error-level ${error.level}">${error.level}</span>
                    <span class="error-message">${escapeHtml(error.message)}</span>
                </div>
            `;
        }).join('');
    } else {
        errorList.innerHTML = '<div class="no-errors">No recent errors</div>';
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Fetch monitor data and update dashboard
 */
async function fetchAndUpdate() {
    try {
        const response = await fetch(MONITOR_URL + '?t=' + Date.now());

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        lastFetchTime = new Date();

        updateDashboard(data);

    } catch (error) {
        console.error('Failed to fetch monitor data:', error);
        updateConnectionStatus('error');

        // Update last update time to show when we last had data
        if (lastFetchTime) {
            document.getElementById('last-update').textContent =
                `Last update: ${formatTimestamp(lastFetchTime.toISOString())} (fetch failed)`;
        }
    }
}

/**
 * Start polling
 */
function startPolling() {
    // Initial fetch
    fetchAndUpdate();

    // Set up interval
    pollTimer = setInterval(fetchAndUpdate, POLL_INTERVAL);
}

/**
 * Stop polling
 */
function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

// Start when page loads
document.addEventListener('DOMContentLoaded', startPolling);

// Stop when page is hidden, restart when visible
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        stopPolling();
    } else {
        startPolling();
    }
});
