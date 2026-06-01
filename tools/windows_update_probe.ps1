param(
  [int]$Limit = 20
)

$ErrorActionPreference = "Stop"

$session = New-Object -ComObject Microsoft.Update.Session
$searcher = $session.CreateUpdateSearcher()
$criteriaList = @(
  "IsInstalled=0",
  "IsInstalled=0 and IsHidden=0",
  "IsInstalled=0 and Type='Software'",
  "IsInstalled=0 and Type='Driver'"
)

foreach ($criteria in $criteriaList) {
  try {
    $result = $searcher.Search($criteria)
    Write-Output "CRITERIA=$criteria COUNT=$($result.Updates.Count)"
    for ($i = 0; $i -lt [Math]::Min($result.Updates.Count, $Limit); $i++) {
      $update = $result.Updates.Item($i)
      $categories = @()
      foreach ($category in $update.Categories) {
        $categories += $category.Name
      }
      Write-Output (" - Type={0} BrowseOnly={1} AutoSelect={2} Title={3} Categories={4}" -f `
        $update.Type, `
        $update.BrowseOnly, `
        $update.AutoSelectOnWebSites, `
        $update.Title, `
        ($categories -join "; "))
    }
  } catch {
    Write-Output "CRITERIA=$criteria ERROR=$($_.Exception.Message)"
  }
}
