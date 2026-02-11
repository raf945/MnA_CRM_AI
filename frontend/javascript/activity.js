// Display activity logs
async function showActivityLog() {
    // Call python rest api for nosql database
    const response = await fetch('/api/activity', {
        method : 'GET',
        headers: { "Accept": "application/json" },
        credentials: "same-origin"
    });

    // Throw error is response is not ok
    if (!response.ok) throw new Error(`Failed: ${response.status}`);

    // Define variable to hold response
    const data = await response.json();

    // Create activity log row
    const tbody = document.getElementById("activity-page-tbody");
    tbody.innerHTML = ''; 
    console.log(data);

    data.activity_log.reverse().forEach(log => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${log.time}</td>
            <td>${log.date}</td>
            <td>${log.details}</td>
        `;

    // Append activity log row to table
    tbody.appendChild(tr);
    });
}