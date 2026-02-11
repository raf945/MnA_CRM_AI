// Load event listeners
const tbody = document.getElementById("leads-page-tbody");
tbody.addEventListener("change", onLeadsPageTaskChange);
tbody.addEventListener("change", onLeadsPageStageChange);
tbody.addEventListener("click", rescheduleClick);

// Before clicking, check in console:
console.log(document.getElementById("leads-id").hidden); // Should be false
console.log(document.querySelectorAll(".leads-page-reschedule-btn")); // Should 

// Get leads to display on page
async function loadLeadsPage() {
    console.log("loadLeadsPage called!");

    // Send get request for leads from postgreSQL database
    const res = await fetch("/api/getleads?source=leadpage", {
    method: "GET",
    headers: { "Accept": "application/json" },
    credentials: "same-origin"
  });

  if (!res.ok) throw new Error(`Failed: ${res.status}`);

  // Wait for data to store in variable
  const data = await res.json();
  const tbody = document.getElementById("leads-page-tbody");
  tbody.innerHTML = "";

  // Sort by date
  data.leads.sort((date2, date1) => {
    return new Date(date2.action_date) - new Date(date1.action_date);
  });

  // For each lead, create a row
  data.leads.forEach((lead) => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${lead.im}</td>
      <td>${lead.company_name}</td>
      <td>${lead.agent_name}</td>
      <td>${lead.email}</td>
      <td>
        <select class="leads-page-task-select" data-lead-id="${lead.id}">
          <option value="contact" ${lead.task === "contact" ? "selected" : ""}>Contact</option>
          <option value="follow_up" ${lead.task === "follow_up" ? "selected" : ""}>Follow up</option>
          <option value="reply" ${lead.task === "reply" ? "selected" : ""}>Reply</option>
        </select>
      </td>
      <td>${lead.action_date}</td>
      <td>
        <select class="leads-page-stage-select" data-lead-id="${lead.id}">
            <option value="new" ${lead.stage === "new" ? "selected" : ""}>New</option>
            <option value="contacted" ${lead.stage === "contacted" ? "selected" : ""}>Contacted</option>
            <option value="in_progress" ${lead.stage === "in_progress" ? "selected" : ""}>In Progress</option>
            <option value="Won" ${lead.stage === "Won" ? "selected" : ""}>Won</option>
            <option value="Lost" ${lead.stage === "Lost" ? "selected" : ""}>Lost</option>
            </select>
        </td>
        <td>
        <div class="row-actions">
          <button class="leads-page-reschedule-btn" data-lead-id="${lead.id}" type="button">Reschedule</button>
          <button class="leads-page-delete-btn" data-lead-id="${lead.id}" type="button">Delete</button>
        </div>
      </td>
    `;

    // Append row to table
    tbody.appendChild(tr);
  });
  }

  // Make a reschedule button function
async function rescheduleClick(e){

  // Only run if reschedule button was clicked
  if (!e.target.classList.contains("leads-page-reschedule-btn")) return;

  const leadId = e.target.dataset.leadId;
  const popup_dialog = document.getElementById("reschedule-dialog");

  popup_dialog.dataset.currentLeadId = leadId;
  
  // Show the dialog
  popup_dialog.showModal();

}

// When submit button is clicked post to restapi
document.getElementById('reschedule-form').addEventListener('submit', async (e) =>
{
  console.log('Reschedule Button clicked! 2')

  // Dont refresh page
  e.preventDefault()

  const modal_dialog = document.getElementById('reschedule-dialog');
  const leadId = modal_dialog.dataset.currentLeadId;
  const newDateTime = document.getElementById('reschedule-date-input').value;

  // Call Rest API
  await fetch(`/api/leads/${leadId}/reschedule`, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    credentials: 'same-origin',
    body: JSON.stringify({action_date:newDateTime})
  });

  // Close pop up modal and load leads again to reflect changes
  modal_dialog.close();
  loadLeadsPage()
});

// When button is deleted
tbody.addEventListener("click", async (e) => {
  const delBtn = e.target.closest(".leads-page-delete-btn");
  if (!delBtn) return;

  console.log("Delete clicked!", delBtn.dataset.leadId);

  // Send lead id of lead that will be deleted
  const leadId = delBtn.dataset.leadId 

  await fetch(`/api/leads/${leadId}/delete`, { 
    method: "DELETE", 
    credentials: "same-origin",
    body: JSON.stringify({leadId}) 
  });

  if (!res.ok) throw new Error(`Failed: ${res.status}`);

  await loadLeadsPage();
});

// When task is changed, update database
async function onLeadsPageTaskChange(e) {
  console.log("onLeadsPageTaskChange triggered!", e.target);

  if (!e.target.classList.contains("leads-page-task-select")) return;

  const leadId = e.target.dataset.leadId;
  const newTask = e.target.value;
  

  // Persist to backend
  const response = await fetch(`/api/leads/${leadId}/task`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ task: newTask })
  });

  console.log("Update response:", response.status);
  
  // Wait for response before loading leads page to see updated lead
  if (response.ok) {
    await loadLeadsPage();
  } else {
    console.error("Failed to update");
  }
}

// When stage is changed, update database
async function onLeadsPageStageChange(e) {
  console.log("onStageChange triggered!", e.target);

  if (!e.target.classList.contains("leads-page-stage-select")) return;

  const leadId = e.target.dataset.leadId;
  const newStage = e.target.value;
  

  // Patch column in backend
  const response = await fetch(`/api/leads/${leadId}/stage`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ stage: newStage })
  });
  // Wait for response before loading leads page to see updated lead
  if (response.ok) {
    await loadLeadsPage();
  } else {
    console.error("Failed to update");
  }
}
