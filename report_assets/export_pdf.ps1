$ErrorActionPreference = "Stop"
$docx = "C:\Users\Ashish\Desktop\SML\SML_Project_Report.docx"
$pdf = "C:\Users\Ashish\Desktop\SML\SML_Project_Report.pdf"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($docx, $false, $true)
    try {
        $doc.ExportAsFixedFormat($pdf, 17)
        Write-Output "exported $pdf"
    } finally {
        $doc.Close($false)
    }
} finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
