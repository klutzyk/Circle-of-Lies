param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$PlayerName = "Tester",
  [int]$MaxRounds = 6,
  [string]$SpeakerId = "ai_1",
  [string[]]$Lines = @(
    "I trust people who show evidence, not confidence.",
    "Jalen, what proof do you actually have?",
    "Mara, I will back you if you give specifics.",
    "Someone here is protecting a liability."
  )
)

$ErrorActionPreference = "Stop"

function Invoke-JsonPost {
  param(
    [string]$Uri,
    [hashtable]$Body
  )
  return Invoke-RestMethod -Method Post -Uri $Uri -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 10)
}

try {
  Write-Host "Starting smoke test against $BaseUrl ..." -ForegroundColor Cyan

  $game = Invoke-JsonPost -Uri "$BaseUrl/api/games" -Body @{
    player_name = $PlayerName
    max_rounds = $MaxRounds
  }

  $gid = $game.summary.game_id
  Write-Host "GameId: $gid" -ForegroundColor Green

  $flavor = Invoke-JsonPost -Uri "$BaseUrl/api/games/$gid/llm/flavor-dialogue" -Body @{
    speaker_id = $SpeakerId
  }

  Write-Host "Provider: $($flavor.provider)" -ForegroundColor Yellow
  Write-Host "Model: $($flavor.model)" -ForegroundColor Yellow
  Write-Host "Flavor: $($flavor.text)"
  Write-Host ""

  foreach ($line in $Lines) {
    $turn = Invoke-JsonPost -Uri "$BaseUrl/api/games/$gid/story-turn" -Body @{
      player_text = $line
    }

    Write-Host "Input: $line" -ForegroundColor Cyan
    Write-Host "Narration: $($turn.story.narration)"
    if ($turn.story.dialogue) {
      foreach ($d in $turn.story.dialogue) {
        Write-Host "$($d.speaker_name): $($d.line)"
      }
    }
    Write-Host "LLM Error: $($turn.story.llm_error)"
    Write-Host "Status: $($turn.summary.status) | Round: $($turn.summary.current_round)/$($turn.summary.max_rounds)"
    Write-Host ""

    if ($turn.summary.status -eq "completed") {
      break
    }
  }

  Write-Host "Smoke test completed." -ForegroundColor Green
}
catch {
  Write-Host "Smoke test failed: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
