function showPdfViewer() {
    document.getElementById('pdfViewer').style.display = 'block';
    document.getElementById('chunksView').style.display = 'none';
    
    // Update button states
    document.getElementById('showPdf').classList.add('active');
    document.getElementById('showChunks').classList.remove('active');
}

function showChunksView() {
    document.getElementById('pdfViewer').style.display = 'none';
    document.getElementById('chunksView').style.display = 'block';
    
    // Update button states
    document.getElementById('showPdf').classList.remove('active');
    document.getElementById('showChunks').classList.add('active');
}

// Initialize with PDF view active
document.addEventListener('DOMContentLoaded', function() {
    showPdfViewer();
});