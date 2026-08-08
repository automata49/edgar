Attribute VB_Name = "Sheet_관심종목_ClickChart"
Option Explicit

'이 코드는 Excel VBA 편집기에서 관심종목 시트 코드 창에 붙여넣으세요.
'D열 Ticker 셀을 클릭하면 Y2 선택 Ticker가 변경되고 통합 차트가 갱신됩니다.

Private Sub Worksheet_SelectionChange(ByVal Target As Range)
    On Error GoTo SafeExit

    If Target.CountLarge <> 1 Then Exit Sub
    If Intersect(Target, Me.Range("D9:D55")) Is Nothing Then Exit Sub
    If Len(Trim$(CStr(Target.Value))) = 0 Then Exit Sub

    Application.EnableEvents = False
    Me.Range("Y2").Value = UCase$(Trim$(CStr(Target.Value)))
    Me.Range("X1").Select
    Me.Calculate

SafeExit:
    Application.EnableEvents = True
End Sub
