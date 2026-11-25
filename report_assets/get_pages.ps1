$ErrorActionPreference = "Stop"
$docx = "C:\Users\Ashish\Desktop\SML\SML_Project_Report.docx"
$json = "C:\Users\Ashish\Desktop\SML\report_assets\pages.json"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($docx, $false, $false)
    try {
        $doc.Repaginate()
        $names = @("bm_certificate", "bm_ack", "bm_abstract", "bm_toc", "bm_ch1", "bm_ch2", "bm_ch3", "bm_ch4", "bm_ch5", "bm_ch6", "bm_ch7", "bm_refs")
        $out = [ordered]@{}
        foreach ($n in $names) {
            if ($doc.Bookmarks.Exists($n)) {
                $out[$n] = $doc.Bookmarks.Item($n).Range.Information(1)
            } else {
                $out[$n] = -1
            }
        }
        $out | ConvertTo-Json | Set-Content -Path $json -Encoding UTF8
        Write-Output ($out | ConvertTo-Json -Compress)
    } finally {
        $doc.Close($false)
    }
} finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
