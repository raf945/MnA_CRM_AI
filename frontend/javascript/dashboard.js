
// If Leads is clicked then show leads page
document.getElementById("lead-button-bar").addEventListener("click", function showPage(){
    document.getElementById("dashboard-id").style.display = 'none'
    document.getElementById("tasks-id").style.display = 'none'
    document.getElementById("activity-id").style.display = 'none'
    document.getElementById("leads-id").style.display = 'block'

    // Show metrics when dashboard is clicked
    const metricsRow = document.querySelector('.metrics-row');
    metricsRow.style.display = 'none';
    loadLeadsPage()
}); 

// If Activity Log is clicked then show activity page
document.getElementById("activity-button-bar").addEventListener("click", function showPage(){
    document.getElementById("dashboard-id").style.display = 'none'
    document.getElementById("tasks-id").style.display = 'none'
    document.getElementById("activity-id").style.display = 'block'
    document.getElementById("leads-id").style.display = 'none'

    // Hide metrics when on anyother page
    const metricsRow = document.querySelector('.metrics-row');
    metricsRow.style.display = 'none';
    showActivityLog()
});
// If Dashboard is clicked then show dashboard
document.getElementById("dashboard-button-bar").addEventListener("click", function showPage(){
    document.getElementById("dashboard-id").style.display = 'block'
    document.getElementById("tasks-id").style.display = 'none'
    document.getElementById("activity-id").style.display = 'none'
    document.getElementById("leads-id").style.display = 'none'

    // Hide metrics when on anyother page
    const metricsRow = document.querySelector('.metrics-row');
    metricsRow.style.display = 'flex'

    loadLeads();
    leadMetrics();
}); 


// If side-bar button is clicked, change colour and main page
const buttons = document.querySelectorAll('.sidebar-item')
buttons.forEach(function(button) {
    button.addEventListener("click", function() {
        buttons.forEach(function(button) {
            button.classList.remove('sidebar-item--active')
        })
        // Just add the class here - no new listener needed!
        button.classList.add('sidebar-item--active')
    })
})


// Open leads dropdown
const addBtn = document.getElementById("add-lead-btn");
const modal = document.getElementById("add-lead-modal");
const cancelBtn = document.getElementById("cancel-lead-modal");

addBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  modal.hidden = !modal.hidden;
});

// If cancel button is clicked, hide modal menu
cancelBtn.addEventListener("click", () => (modal.hidden = true));

document.addEventListener("click", (e) => {

  if (!e.target.closest(".add-lead-wrapper")) modal.hidden = true;
});


// Open account dropdown
const accountBtn = document.getElementById("check-account-btn");
const accountMenu = document.getElementById("account-menu");
const closeAccountMenu = document.getElementById("close-account-menu");

// On click, open account menu
accountBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  accountMenu.hidden = !accountMenu.hidden;

  const leadModal = document.getElementById("add-lead-modal");
  if (leadModal) leadModal.hidden = true;
});


// To close account menu, click button and set html tag to hidden
closeAccountMenu.addEventListener("click", () => {
  accountMenu.hidden = true;
});

document.addEventListener("click", (e) => {
  if (!e.target.closest(".account-wrapper")) accountMenu.hidden = true;
});


// Save information from leads field when we click save
leadFields = document.querySelectorAll(".lead-field")

let leadData;

document.getElementById('modal-save-button').onclick = function() {
    document.getElementById('save-error-btn').style.display = 'none';

    // Reset error message
    const emailError = document.getElementById('email-error-position');
    if (emailError) {
        emailError.style.display = 'none'
    }

    // If the user hasnt filled out all fields, display error
    let x = 0
    while(x < leadFields.length ){
        if (leadFields[x].value.trim() === ""){
            document.getElementById('save-error-btn').style.display = 'block'
            return
        } 
        x++
    }

    // object to hold structured lead data
    leadData = {
        im: leadFields[0].value,
        company_name: leadFields[1].value,
        agent_name: leadFields[2].value,
        email: leadFields[3].value,
        task: leadFields[4].value,
        date: leadFields[5].value
    };

    // post lead info to /api/leads endpoint
    fetch("/api/leads", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(leadData),
    })
    .then(async (res) => {
    const text = await res.text();

    // If google cloud function email validator deems email format to be incorrect, show error message to user
    if (text.includes("Email format incorrect")) {
      emailError.style.display = 'block'
      throw new Error("Email validation failed")
    } else {
      // Hide menu
      const leadModal = document.getElementById("add-lead-modal");
      leadModal.hidden = true;
      // Empty fields
      document.getElementById('im-number-input').value = '';
      document.getElementById('company-name-input').value = '';
      document.getElementById('agent-name-input').value = '';
      document.getElementById('email-input').value = '';
      document.getElementById('task-input').selectedIndex = 0;
      document.getElementById('date-input').selectedIndex = 0;
      // Display leads
      loadLeads();

    }


    // For debugging
    console.log("STATUS:", res.status);
    console.log("RAW RESPONSE:", text);
    return text ? JSON.parse(text) : null;
    })
    .then((data) => console.log("Saved:", data))
    .catch((err) => console.error("Error:", err));

};



// Sign out of page
document.getElementById("sign-out-btn").onclick = async function () {
  const responseSignOut = await fetch("/logout", {
    method: "POST",
    credentials: "same-origin"
  });

  // If post successful, redirect to login page otherwise show error message
  if (responseSignOut.ok) {
    window.location.href = "/login";
  } else {
    console.log("Logout failed:", responseSignOut.status);
  }
};

// Get leads to display on page
async function loadLeads() {
  const res = await fetch("/api/getleads?source=dashboard", {
    method: "GET",
    headers: { "Accept": "application/json" },
    credentials: "same-origin"
  });

  if (!res.ok) throw new Error(`Failed: ${res.status}`);

  // Store incomming json data in data variable and get the leads container id into tbody variable to append rows of data
  const data = await res.json();
  const tbody = document.getElementById("leads-tbody");
  tbody.innerHTML = "";

  // Sort by date
  data.leads.sort((date2, date1) => {
    return new Date(date2.action_date) - new Date(date1.action_date);
  });


  // For each lead, create a row
  data.leads.forEach((lead) => {
    const tr = document.createElement("tr");

    // Maximum 5 rows for today's tasks
    if (tbody.children.length === 5) {
      return
    }

    // Construct HTML of lead info
    tr.innerHTML = `
      <td>${lead.im}</td>
      <td>${lead.company_name}</td>
      <td>${lead.agent_name}</td>
      <td>${lead.email}</td>
      <td>
        <select class="task-select" data-lead-id="${lead.id}">
          <option value="contact" ${lead.task === "contact" ? "selected" : ""}>Contact</option>
          <option value="follow_up" ${lead.task === "follow_up" ? "selected" : ""}>Follow up</option>
          <option value="reply" ${lead.task === "reply" ? "selected" : ""}>Reply</option>
        </select>
      </td>
      <td>${lead.action_date}</td>
      <td>
        <select class="stage-select" data-lead-id="${lead.id}">
            <option value="new" ${lead.stage === "new" ? "selected" : ""}>New</option>
            <option value="contacted" ${lead.stage === "contacted" ? "selected" : ""}>Contacted</option>
            <option value="in_progress" ${lead.stage === "in_progress" ? "selected" : ""}>In Progress</option>
            <option value="Won" ${lead.stage === "Won" ? "selected" : ""}>Won</option>
            <option value="Lost" ${lead.stage === "Lost" ? "selected" : ""}>Lost</option>
            </select>
        </td>
        <td>
        <div class="row-actions">
          <button class="complete-btn" data-lead-id="${lead.id}" type="button">Complete</button>
          <button class="reschedule-btn" data-lead-id="${lead.id}" type="button">Reschedule</button>
        </div>
      </td>
    `;

    // Append rows to table container
    tbody.appendChild(tr);
  });

  // Add event listener to all buttons in the rows
  tbody.addEventListener("change", onTaskChange);
  tbody.addEventListener("change", onStageChange);
  tbody.addEventListener("click", onCompleteClick);
  tbody.addEventListener("click", rescheduleClick);
  }

  // Reschedule function that gets a new date from the user, then posts it to the sql database via the rest api endpoint
async function rescheduleClick(e){

  // Only run if reschedule button was clicked
  if (!e.target.classList.contains("reschedule-btn")) return;

  const leadId = e.target.dataset.leadId;
  const popup_dialog = document.getElementById("reschedule-dialog");

  popup_dialog.dataset.currentLeadId = leadId;
  
  // Show the dialog
  popup_dialog.showModal();

}

// When submit button is clicked post to restapi
document.getElementById('reschedule-form').addEventListener('submit', async (e) =>
{
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
  loadLeads();
});


// Give user option to close pop up modal
document.getElementById('cancel-reschedule').addEventListener('click', () => {
  document.getElementById('reschedule-dialog').close();
});


// When user clicks complete button, update status of lead to complete
async function onCompleteClick(e) {
  const btn = e.target.closest(".complete-btn");
  if (!btn) return;

  const leadId = btn.dataset.leadId;
  const row = btn.closest("tr");
  const parent = row.parentElement;
  const nextSibling = row.nextSibling;

  // Remove row from UI
  row.classList.add("row-exit");
  setTimeout(() => row.remove(), 200);

  // post to database and look for ok response
  const res = await fetch(`/api/leads/${leadId}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({})
  });

  if (res.ok === false) {
    row.classList.remove("row-exit");

    // If it was removed already, re-insert
    if (!row.isConnected) {
      if (nextSibling) parent.insertBefore(row, nextSibling);
      else parent.appendChild(row);
    }

    // Show error if frontend cant communicate with data layer
    alert("Couldn’t complete. Try again.");
    throw new Error(`Complete failed: ${res.status}`);
  }
}



// When task is changed, update sql database
async function onTaskChange(e) {
  if (!e.target.classList.contains("task-select")) return;

  const leadId = e.target.dataset.leadId;
  const newTask = e.target.value;
  
    try {
      // Send patch to backend
      const response = await fetch(`/api/leads/${leadId}/task`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ task: newTask })
      });
      
      if (!response.ok) {
        console.error("Failed to update task:", response.status);
        alert("Failed to update task");
        return;
      }
      
      console.log("Task updated successfully");
      // If CORS incorrect or server failure show error
    } catch (error) {
      console.error("Error updating task:", error);
      alert("Error updating task");
    }
  }


// When stage is changed, update database
async function onStageChange(e) {
  if (!e.target.classList.contains("stage-select")) return;

  const leadId = e.target.dataset.leadId;
  const newStage = e.target.value;
  

  try {
      // Patch column
      const response = await fetch(`/api/leads/${leadId}/stage`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ stage: newStage })
      });
      
      if (!response.ok) {
        console.error("Failed to update stage:", response.status);
        alert("Failed to update stage");
        return;
      }
      
      console.log("Stage updated successfully");
      // Show server error or CORS problem
    } catch (error) {
      console.error("Error updating stage:", error);
      alert("Error updating stage");
    }
}
// Leads after changing task or stage
loadLeads();

// Get task metric info via a aggregate sql query
async function leadMetrics(){
  res = await fetch("/api/leads/metrics", {
    method: "GET",
    headers: { "Accept": "application/json" },
    credentials: "same-origin"
  });

  // Get the data
  const data = await res.json();

  // Update over due tasks
  const overDue = document.getElementById("tasks-overdue-count");
  overDue.textContent = data.tasks_status;

  // Update tasks due today
  const dueToday = document.getElementById("tasks-due-count");
  dueToday.textContent = data.tasks_due_count;

  // Update open leads
  const openLeads = document.getElementById("open-leads-count");
  openLeads.textContent = data.tasks_open;
};

leadMetrics()
