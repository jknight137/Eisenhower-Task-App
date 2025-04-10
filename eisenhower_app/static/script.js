// static/script.js
function checkForNotifications() {
  // Assume we have a function to get tasks from the server
  getTasks().then((tasks) => {
    const now = new Date();
    tasks.forEach((task) => {
      if (task.due_date && new Date(task.due_date) < now) {
        showNotification(`Task "${task.title}" is overdue!`);
      } else if (task.due_date) {
        const dueDate = new Date(task.due_date);
        const diff = dueDate - now;
        if (diff < 24 * 60 * 60 * 1000) {
          // Less than a day left
          showNotification(`Task "${task.title}" is due in less than a day!`);
        }
      }
    });
  });
}

function showNotification(message) {
  alert(message); // Or use a more sophisticated notification method
}
// static/script.js
async function subscribeToPush() {
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: "your_vapid_public_key", // Generate via push service
  });
  fetch("/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(subscription),
  });
}

if ("PushManager" in window) {
  subscribeToPush();
}

window.setInterval(checkForNotifications, 60000); // Check every minute
