document.addEventListener('DOMContentLoaded', function() {
    const modeOptions = document.querySelectorAll('.mode-option');
    const documentSelection = document.getElementById('documentSelection');
    const subjectSelection = document.getElementById('subjectSelection');
    const startChatBtn = document.getElementById('startChatBtn');
    const documentSelect = document.getElementById('id_document');
    const subjectSelect = document.getElementById('id_subject');
    
    // Handle mode selection
    modeOptions.forEach(option => {
        option.addEventListener('click', function() {
            const mode = this.getAttribute('data-mode');
            const radio = this.querySelector('input[type="radio"]');
            
            // Clear previous selections
            modeOptions.forEach(opt => opt.classList.remove('selected'));
            documentSelection.style.display = 'none';
            subjectSelection.style.display = 'none';
            
            // Select current option
            this.classList.add('selected');
            radio.checked = true;
            
            // Show appropriate selection
            if (mode === 'document') {
                documentSelection.style.display = 'block';
            } else if (mode === 'subject') {
                subjectSelection.style.display = 'block';
            }
            
            checkFormValidity();
        });
    });
    
    // Handle document/subject selection changes
    documentSelect.addEventListener('change', checkFormValidity);
    subjectSelect.addEventListener('change', checkFormValidity);
    
    function checkFormValidity() {
        const selectedMode = document.querySelector('input[name="chat_mode"]:checked');
        let isValid = false;
        
        if (selectedMode) {
            if (selectedMode.value === 'document' && documentSelect.value) {
                isValid = true;
            } else if (selectedMode.value === 'subject' && subjectSelect.value) {
                isValid = true;
            }
        }
        
        startChatBtn.disabled = !isValid;
    }
    
    // Handle form submission
    document.getElementById('chatModeForm').addEventListener('submit', function(e) {
        if (startChatBtn.disabled) {
            e.preventDefault();
        }
    });
});