$file = ".\templates\sales\pos.html"

$backup = Get-ChildItem "$file.bak_*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $backup) {
    Write-Host "No backup found - aborting." -ForegroundColor Red
    exit
}
Copy-Item $backup.FullName $file -Force
Write-Host "Restored from backup: $($backup.Name)" -ForegroundColor Green

$newBackup = "$file.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $file $newBackup
Write-Host "New backup created: $newBackup" -ForegroundColor Green

$content = Get-Content $file -Raw

$old = "function onPaymentChange() {`r`n  const method = document.getElementById('paymentMethod').value;`r`n  document.getElementById('cashFields').style.display = method === 'cash' ? 'block' : 'none';`r`n  document.getElementById('momoFields').style.display = method === 'momo' ? 'block' : 'none';`r`n  document.getElementById('splitFields').style.display = method === 'split' ? 'block' : 'none';`r`n  document.getElementById('creditFields').style.display = method === 'credit' ? 'block' : 'none';`r`n}"

$new = "function onPaymentChange() {`r`n  const method = document.getElementById('paymentMethod').value;`r`n  const sections = {`r`n    cash: document.getElementById('cashFields'),`r`n    momo: document.getElementById('momoFields'),`r`n    split: document.getElementById('splitFields'),`r`n    credit: document.getElementById('creditFields'),`r`n  };`r`n  Object.keys(sections).forEach(function(key) {`r`n    const el = sections[key];`r`n    const isActive = (key === method);`r`n    el.style.display = isActive ? 'block' : 'none';`r`n    el.querySelectorAll('input, select, textarea').forEach(function(field) {`r`n      field.disabled = !isActive;`r`n    });`r`n  });`r`n}"

if ($content -notmatch [regex]::Escape($old)) {
    Write-Host "WARNING: exact JS block not found - no changes made to JS." -ForegroundColor Red
    exit
}

$content = $content -replace [regex]::Escape($old), $new
Set-Content -Path $file -Value $content -NoNewline
Write-Host "JS patched: fields now disabled when hidden." -ForegroundColor Green

$check = Get-Content $file -Raw
if ($check -match 'field\.disabled = !isActive') {
    Write-Host "SUCCESS: patch applied and verified." -ForegroundColor Green
} else {
    Write-Host "WARNING: verification failed." -ForegroundColor Red
}

Write-Host "Restart your dev server and test MoMo, Split, Cash, Credit checkouts." -ForegroundColor Cyan
