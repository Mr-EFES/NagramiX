"""Check the exact generated Texture bridge, including the original214 failure."""
from validate_quick_format import block
from validate_private_temporary_transcription import execute
from pip_preview_continuity_apple import fixture,texture_background_contract
import subprocess


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    declaration=texture_background_contract(source)
    adapter=block(fixture(source,source),'class ASDisplayNode {')
    boundary='''import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
#if canImport(UIKit)
import UIKit
#else
final class UIColor {static let black=UIColor()}
final class CALayer {var cornerRadius:CGFloat=0}
final class UIView {
 var backgroundColor:UIColor?,frame=CGRect.zero
 var bounds:CGRect{frame}
 var isUserInteractionEnabled=true,clipsToBounds=false
 let layer=CALayer()
 func addSubview(_ view:UIView){}
 func removeFromSuperview(){}
}
#endif
'''
    tests='''
final class Poster:ASDisplayNode {}
@main struct Tests {
 static func main(){
  let poster=Poster()
  poster.backgroundColor = .black
  precondition(poster.view.backgroundColor != nil)
  precondition(poster.backgroundColor != nil)
  poster.backgroundColor=nil
  precondition(poster.view.backgroundColor==nil)
  poster.view.backgroundColor = .black
  precondition(poster.backgroundColor != nil)
  poster.view.backgroundColor=nil
  precondition(poster.backgroundColor==nil)
  print("Texture UIKit adapter: inherited UIColor? setter/getter and backing UIView passed")
 }
}
'''
    code=boundary+adapter+'\n'+tests
    runs=execute(swiftc,folder,'texture-poster-adapter',code)
    property=' var backgroundColor:UIColor?{get{view.backgroundColor}set{view.backgroundColor=newValue}}'
    assert code.count(property)==1
    old=folder/'original214.swift';old.write_text(code.replace(property,''))
    negatives=[]
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        p=subprocess.run([str(swiftc),'-swift-version','5','-parse-as-library','-warnings-as-errors','-typecheck','-module-cache-path',str(folder/'cache'),*flags,str(old)],capture_output=True,text=True)
        assert p.returncode and "has no member 'backgroundColor'" in p.stderr,p.stdout+p.stderr
        negatives.append({'mode':mode,'original214_missing_member_rejected':True})
    return {'native_declaration':declaration,'executions':runs,'original214':negatives,'scope':'Exact generated ASDisplayNode adapter and actual poster assignment. Host execution uses explicit UIColor/UIView boundaries unless UIKit is importable; a separate iPhoneOS poster probe checks real UIKit. Native Texture implementation/full application are separate.'}
